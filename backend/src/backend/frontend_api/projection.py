"""Analysis (graph data) → the front-end tree Critério → Regra → Evidência, with accepted contestations applied
on top of the stored analysis (which is never modified)."""

from backend.analyses.models import Analysis
from backend.catalog.models import CRITERIA_ORDER, Catalog, CatalogRule
from backend.criteria.schemas import CriterionResult, EvidenceItem, RuleRun
from backend.frontend_api import schemas as fe
from backend.graph.scoring import RuleScore, score_criterion, score_rule
from backend.graph.states import column_of
from backend.projects.models import Project
from backend.review.models import Contestation

RULE_METHOD = "Nota = positivas ÷ (positivas + negativas) × 100; a mesma fonte conta uma vez. Indicador, não decide a classe."
CRITERION_METHOD = ("Média simples das regras com evidência. Regras sem evidência, N/A, não executadas e "
                    "NOV-W1/W2/W8 (informativas) ficam fora. Indicador, não decide a classe.")


def distribute(total: int, weights: list[float]) -> list[int]:
    """Integer parts proportional to `weights` that add up exactly to `total` (largest remainder)."""
    if not weights:
        return []
    weight_sum = sum(weights) or 1
    raw = [total * w / weight_sum for w in weights]
    parts = [int(x) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: raw[i] - parts[i], reverse=True)
    for i in order[: total - sum(parts)]:
        parts[i] += 1
    return parts


def criterion_node_id(catalog: Catalog, criterion: str) -> str:
    return f"crit-{catalog.criteria[criterion].chave}"


def rule_node_id(rule_id: str) -> str:
    return f"rule-{rule_id.lower()}"


def _apply_contestations(results: dict[str, CriterionResult], contestations: list[Contestation]):
    """Copies of the results with accepted contestation changes applied (polarity, removed and added evidence)."""
    copies = {c: r.model_copy(deep=True) for c, r in results.items()}
    state_overrides: dict[str, str] = {}
    adjusted_ids: set[str] = set()
    for contestation in contestations:
        resolution = contestation.resolution
        if not resolution or resolution.verdict != "accepted":
            continue
        for result in copies.values():
            for run in result.rules:
                kept = []
                for evidence in run.evidences:
                    if evidence.id in resolution.removed_evidence_ids:
                        continue
                    if evidence.id in resolution.flipped_evidence_ids:
                        evidence.polarity = "negativa" if evidence.polarity == "positiva" else "positiva"
                        adjusted_ids.add(evidence.id)
                    kept.append(evidence)
                run.evidences = kept
                added = [e for e in resolution.added_evidences if e.rule_id == run.rule_id]
                if added:
                    run.evidences += added
                    run.status = "executada"
                    adjusted_ids.update(e.id for e in added)
        if resolution.new_state and resolution.criterion:
            state_overrides[resolution.criterion] = resolution.new_state
    return copies, state_overrides, adjusted_ids


def _rule_view(catalog: Catalog, run: RuleRun, rule: CatalogRule | None, score: RuleScore, documents: dict[str, str],
               adjusted: set[str]) -> fe.Rule:
    evidences = []
    for item in run.evidences:
        evidences.append(_evidence_view(item, documents, counted=item.id in score.counted_evidence_ids,
                                        adjusted=item.id in adjusted))
    positives = [e for e in evidences if e.polarity == "positive" and e.counted]
    points = distribute(score.score or 0, [1] * len(positives))
    point_of = {e.id: p for e, p in zip(positives, points, strict=True)}
    explanation = None
    if score.score is not None:
        explanation = fe.ScoreExplanation(
            method=RULE_METHOD,
            baseline=0,
            factors=[fe.ScoreFactor(kind="evidence", ref_id=e.id, label=e.title, points=point_of.get(e.id, 0))
                     for e in evidences if e.counted],
        )
    sources = rule.fontes_normativas if rule else []
    reason = run.reason or run.note
    return fe.Rule(
        id=rule_node_id(run.rule_id),
        code=run.rule_id,
        name=rule.titulo if rule else run.rule_id,
        score=score.score,
        explanation=" ".join(filter(None, [rule.explicacao_simples if rule else None, reason])),
        normative_source=fe.Reference(label=sources[0] if sources else "Catálogo de regras", citation=rule.o_que_verificar if rule else None),
        evidences=evidences,
        score_explanation=explanation,
        counts=fe.Counts(positive=score.positive, negative=score.negative),
        status=run.status,
        status_reason=reason,
        in_mean=score.in_mean,
        block=rule.bloco if rule else "",
        normative_sources=sources,
    )


def _evidence_view(item: EvidenceItem, documents: dict[str, str], counted: bool, adjusted: bool) -> fe.Evidence:
    file_name = item.source_alias.split("#")[0] if item.origin == "doc" else None
    return fe.Evidence(
        id=item.id,
        title=f"{item.rule_id} · {item.source_alias}",
        polarity="positive" if item.polarity == "positiva" else "negative",
        explanation=item.explanation,
        project_excerpt=fe.ProjectExcerpt(document_id=documents.get(file_name), file_name=file_name, page=item.page,
                                          excerpt=item.quote) if item.origin == "doc" else None,
        references=[fe.Reference(label=item.source_alias, citation=item.quote, url=item.url)] if item.origin == "web" else [],
        rule_code=item.rule_id,
        source=fe.EvidenceSource(origin=item.origin, fragment_id=item.source_id if item.origin == "doc" else None,
                                 alias=item.source_alias, nature=item.nature, url=item.url,
                                 published_date=item.published_date, captured_at=item.captured_at, query=item.query),
        counted=counted,
        adjusted=adjusted,
    )


def project_analysis(catalog: Catalog, analysis: Analysis, project: Project, contestations: list[Contestation]) -> fe.Analysis:
    documents = {d.file_name: d.id for d in project.active_documents()}
    relevant = [c for c in contestations if c.analysis_id == str(analysis.id)]
    results, state_overrides, adjusted = _apply_contestations(analysis.criteria, relevant)
    criteria = []
    for criterion in CRITERIA_ORDER:
        info = catalog.criteria[criterion]
        result = results.get(criterion) or CriterionResult(criterion=criterion)
        state = analysis.states.get(criterion)
        scores = [score_rule(run, catalog.get(run.rule_id)) for run in result.rules]
        rules = [_rule_view(catalog, run, catalog.get(run.rule_id), score, documents, adjusted)
                 for run, score in zip(result.rules, scores, strict=True)]
        criterion_score = score_criterion(scores)
        in_mean = [r for r in rules if r.in_mean and r.score is not None]
        explanation = None
        if criterion_score is not None:
            parts = distribute(criterion_score, [r.score or 0 for r in in_mean]) if any(r.score for r in in_mean) else [0] * len(in_mean)
            explanation = fe.ScoreExplanation(
                method=CRITERION_METHOD,
                baseline=0,
                factors=[fe.ScoreFactor(kind="rule", ref_id=r.id, label=f"{r.code} {r.name}", points=p, value=r.score,
                                        weight=round(1 / len(in_mean), 4)) for r, p in zip(in_mean, parts, strict=True)],
            )
        current_state = state_overrides.get(criterion) or (state.state if state else None)
        criteria.append(fe.Criterion(
            id=criterion_node_id(catalog, criterion),
            key=info.chave,
            name=info.nome,
            score=criterion_score,
            summary=state.justification if state and state.justification else (state.error if state and state.error else ""),
            rules=rules,
            score_explanation=explanation,
            criterion_id=criterion,
            state=current_state,
            column=column_of(criterion, current_state, catalog) if current_state else None,
            llm_state=state.llm_state if state else None,
            gates=state.gates if state else [],
            normative_source=info.fonte_normativa,
            decisive_evidence_ids=state.decisive_evidence_ids if state else [],
        ))
    suggestion = analysis.suggestion
    adjustments = [
        fe.AnalysisChangeRead(**change.model_dump(), contestation_id=str(c.id))
        for c in relevant if c.resolution and c.resolution.verdict == "accepted"
        for change in c.resolution.changes
    ]
    return fe.Analysis(
        id=str(analysis.id),
        project_id=analysis.project_id,
        generated_at=analysis.finished_at,
        criteria=criteria,
        adjustments=adjustments,
        version=analysis.version,
        status=analysis.status,
        suggested_class=suggestion.suggested_class if suggestion else None,
        inconsistent=suggestion.inconsistent if suggestion else True,
        class_reason=suggestion.reason if suggestion else None,
        decision_path=suggestion.path if suggestion else [],
        incomplete=suggestion.incomplete if suggestion else [],
        caveat=fe.Caveat(scope=suggestion.caveat.recorte_sustentado, limitation=suggestion.caveat.limitacao,
                         evidence_needed=suggestion.caveat.evidencia_necessaria) if suggestion and suggestion.caveat else None,
        missing_link=fe.MissingLink(link=suggestion.missing_link.elo_ausente,
                                    evidence_to_request=suggestion.missing_link.evidencias_a_solicitar)
        if suggestion and suggestion.missing_link else None,
        divergences=[fe.DivergenceRead(criterion_key=catalog.criteria[c].chave, statement=d.statement,
                                       testimony_fragment_id=d.testimony_fragment_id, record_fragment_id=d.record_fragment_id,
                                       record_alias=d.record_alias)
                     for c, r in analysis.criteria.items() for d in r.divergences],
        missing_links=[f"{l.description} — solicitar: {l.evidence_to_request}" for r in analysis.criteria.values() for l in r.missing_links],
        gaps=[fe.GapRead(rule_code=run.rule_id, status=run.status, reason=run.reason or "-")
              for r in analysis.criteria.values() for run in r.rules if run.status in ("na", "parcial", "nao_executada", "sem_evidencia")],
        versions=fe.VersionsRead.model_validate(analysis.versions.model_dump()),
    )
