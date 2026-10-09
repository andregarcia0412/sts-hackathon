"""The model re-reads a contested node with the analyst's argument as data. The result is an adjustment recorded
on the contestation (before/after); the stored analysis is never modified."""

from typing import Literal

from pydantic import BaseModel

from backend.analyses.models import Analysis, CanonicalRecord
from backend.analyses.orchestrator import AnalysisService
from backend.catalog.models import Catalog
from backend.criteria.common import DATA_NOT_INSTRUCTIONS, argument_block
from backend.criteria.doc_sub import run_doc_sub
from backend.criteria.schemas import EvidenceItem
from backend.criteria.web_sub import run_web_sub
from backend.graph.scoring import score_criterion, score_rule
from backend.graph.states import judge_state, numeric_record_in
from backend.llm.prompts import register_prompt
from backend.review.models import AnalysisChange, Contestation, ContestationResolution


class ContestationError(ValueError):
    pass


class ContestationVerdictOut(BaseModel):
    verdict: Literal["accepted", "maintained"]
    explicacao: str


VERDICT_SYSTEM = register_prompt(
    "review.contestation",
    """Um analista contestou uma evidência que você apontou para uma regra da Lei do Bem. Releia o trecho e a
fonte com o argumento do analista. Aceite ("accepted") só se o argumento se verifica no texto da fonte;
caso contrário mantenha ("maintained"). Explique em até 3 frases, sem inventar fatos.
"""
    + DATA_NOT_INSTRUCTIONS,
)


def parse_node(catalog: Catalog, node_id: str) -> tuple[str, str | None, str | None]:
    parts = node_id.split(".")
    criterion = next((c for c, info in catalog.criteria.items() if f"crit-{info.chave}" == parts[0]), None)
    if criterion is None:
        raise ContestationError(f"unknown criterion node {parts[0]!r}")
    rule_id = parts[1].removeprefix("rule-").upper() if len(parts) > 1 else None
    if rule_id and (catalog.get(rule_id) is None or catalog.get(rule_id).criterio != criterion):
        raise ContestationError(f"unknown rule node {parts[1]!r}")
    return criterion, rule_id, parts[2] if len(parts) > 2 else None


def _scores(catalog, result, rule_id):
    runs = {r.rule_id: r for r in result.rules}
    scores = [score_rule(r, catalog.get(r.rule_id)) for r in result.rules]
    return next(s.score for s in scores if s.rule_id == rule_id), score_criterion(scores), runs


def _score_changes(catalog, criterion, rule_id, before_result, after_result, labels) -> list[AnalysisChange]:
    rule_before, crit_before, _ = _scores(catalog, before_result, rule_id)
    rule_after, crit_after, _ = _scores(catalog, after_result, rule_id)
    changes = []
    if rule_before != rule_after:
        changes.append(AnalysisChange(node_id=labels["rule_node"], node_label=labels["rule"], field="score",
                                      before=rule_before, after=rule_after))
    if crit_before != crit_after:
        changes.append(AnalysisChange(node_id=labels["criterion_node"], node_label=labels["criterion"], field="score",
                                      before=crit_before, after=crit_after))
    return changes


async def reanalyze(service: AnalysisService, contestation: Contestation) -> ContestationResolution:
    catalog = service.catalog
    analysis = await Analysis.get(contestation.analysis_id)
    criterion, rule_id, evidence_id = parse_node(catalog, contestation.node_id)
    result = analysis.criteria.get(criterion)
    info = catalog.criteria[criterion]
    labels = {"criterion_node": f"crit-{info.chave}", "criterion": info.nome,
              "rule_node": f"crit-{info.chave}.rule-{(rule_id or '').lower()}", "rule": rule_id or ""}

    if evidence_id:
        run = result.rule(rule_id) if result else None
        evidence = next((e for e in (run.evidences if run else []) if e.id == evidence_id), None)
        if evidence is None:
            raise ContestationError(f"unknown evidence node {evidence_id!r}")
        user = (f"Regra {rule_id}: {catalog.get(rule_id).o_que_verificar}\nPolaridade atual: {evidence.polarity}\n"
                f"Motivo da contestação: {contestation.reason}\n<fragmentos>\nFonte {evidence.source_alias}: "
                f"\"{evidence.quote}\"\nJustificativa do sistema: {evidence.explanation}\n</fragmentos>"
                + argument_block(contestation.argument))
        out = await service.llm.structured(
            [{"role": "system", "content": VERDICT_SYSTEM}, {"role": "user", "content": user}], ContestationVerdictOut,
            role="judge",
        )
        resolution = ContestationResolution(verdict=out.verdict, explanation=out.explicacao, criterion=criterion)
        if out.verdict == "maintained" or contestation.reason not in ("polarity", "wrong_excerpt"):
            return resolution
        after = result.model_copy(deep=True)
        after_run = after.rule(rule_id)
        if contestation.reason == "polarity":
            flipped = "negativa" if evidence.polarity == "positiva" else "positiva"
            next(e for e in after_run.evidences if e.id == evidence_id).polarity = flipped
            resolution.flipped_evidence_ids = [evidence_id]
            resolution.changes.append(AnalysisChange(
                node_id=contestation.node_id, node_label=contestation.node_label, field="polarity",
                before="positive" if evidence.polarity == "positiva" else "negative",
                after="positive" if flipped == "positiva" else "negative"))
        else:
            after_run.evidences = [e for e in after_run.evidences if e.id != evidence_id]
            resolution.removed_evidence_ids = [evidence_id]
        resolution.changes += _score_changes(catalog, criterion, rule_id, result, after, labels)
        return resolution

    record = await CanonicalRecord.find_one(CanonicalRecord.analysis_id == contestation.analysis_id)
    if rule_id:
        rule = catalog.get(rule_id)
        if rule.bloco == "web":
            fresh = await run_web_sub(service.llm, catalog, criterion, [rule], record.canonical, service.providers(),
                                      service.settings.web_queries_per_front, service.settings.web_results_per_query,
                                      service.settings.web_fetch_per_front, analysis.criteria["NOV"].closest_doc,
                                      analyst_argument=contestation.argument)
        else:
            fresh = await run_doc_sub(service.llm, catalog, criterion, [rule], record.canonical,
                                      service.settings.prompt_max_table_rows, analyst_argument=contestation.argument)
        fresh_run = fresh.rule(rule_id)
        known = {e.id for e in result.rule(rule_id).evidences} if result.rule(rule_id) else set()
        added: list[EvidenceItem] = [e for e in (fresh_run.evidences if fresh_run else []) if e.id not in known]
        if not added:
            reason = fresh_run.reason if fresh_run and fresh_run.reason else "nenhum trecho novo sustenta a regra"
            return ContestationResolution(verdict="maintained", criterion=criterion,
                                          explanation=f"Releitura com o argumento não encontrou evidência nova: {reason}.")
        after = result.model_copy(deep=True)
        run = after.rule(rule_id)
        run.evidences += added
        run.status = "executada"
        return ContestationResolution(
            verdict="accepted", criterion=criterion, added_evidences=added,
            explanation="Releitura com o argumento encontrou: " + "; ".join(f'[{e.source_alias}] "{e.quote}"' for e in added),
            changes=_score_changes(catalog, criterion, rule_id, result, after, labels),
        )

    current = analysis.states.get(criterion)
    state = await judge_state(service.llm, catalog, result, numeric_record_in(analysis.criteria),
                              analyst_argument=contestation.argument)
    if state.state is None or current is None or state.state == current.state:
        return ContestationResolution(verdict="maintained", criterion=criterion,
                                      explanation=state.justification or state.error or "Estado mantido.")
    return ContestationResolution(
        verdict="accepted", criterion=criterion, new_state=state.state, explanation=state.justification,
        changes=[AnalysisChange(node_id=contestation.node_id, node_label=contestation.node_label, field="state",
                                before=current.state, after=state.state)],
    )
