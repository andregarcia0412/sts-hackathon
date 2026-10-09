"""Consistency between criteria (spec 02, part A): a source that Novelty used as proof that the prior reference
already provided the function cannot, at the same time, sustain Creativity or Uncertainty.

Deterministic and never deletes: the affected positive evidence of CRI/INC keeps its polarity, gains an
`adjustment` and leaves the score. Behind CONSISTENCY_NEUTRALIZE (off by default)."""

import re

from pydantic import BaseModel, Field

from backend.catalog.models import Catalog
from backend.checks.models import ChecksReport
from backend.criteria.schemas import Adjustment, CriterionResult

NEUTRALIZED = ("CRI", "INC")
# Text markers of containment by the prior reference, only as reinforcement of the catalog rules: "anterior" alone
# matches "versão anterior", so a source marked only by text is a warning unless CONSISTENCY_USE_TEXT_MARKERS=true.
CONTAINMENT_RE = re.compile(
    r"j[áa] (?:fornec\w*|existia|existe|era|estava)|anterior|adapta[çc][ãa]o de tecnologia|j[áa] dominad[oa]|"
    r"j[áa] conhecid[oa]|tecnologia j[áa] existente|j[áa] admitid[oa]", re.IGNORECASE)
NUMERIC_NATURES = {"registro_primario", "derivado"}


class Neutralized(BaseModel):
    evidence_id: str
    rule_id: str
    source_id: str
    by_rule: str


class ConsistencyReport(BaseModel):
    reference_sources: dict[str, str] = Field(default_factory=dict)  # source id → NOV rule that marked it
    neutralized: list[Neutralized] = Field(default_factory=list)
    inverted: list[Neutralized] = Field(default_factory=list)  # INC-D2 × CHK-PERGUNTA: counted as negative
    warnings: list[str] = Field(default_factory=list)


def _inc_d2_against_known_solution(results: dict[str, CriterionResult], checks: ChecksReport | None,
                                   report: ConsistencyReport) -> None:
    """A registered question that already names the known solution is routine: INC-D2 support quoting it counts
    as negative (kept, with the original polarity and an adjustment)."""
    question = checks.get("CHK-PERGUNTA") if checks else None
    if question is None or not question.facts.get("aplica_solucao_conhecida"):
        return
    flagged = [q for q in question.facts.get("perguntas", []) if q.get("aplica_solucao_conhecida")]
    texts = [" ".join(q["pergunta"].lower().split()) for q in flagged]
    fragments = {q["fragmento"] for q in flagged}
    run = results["INC"].rule("INC-D2") if "INC" in results else None
    for item in run.evidences if run else []:
        quote = " ".join(item.quote.lower().split())
        if item.polarity != "positiva" or item.adjustment is not None:
            continue
        if item.source_id in fragments or any(t in quote or (len(quote) > 20 and quote in t) for t in texts):
            item.adjustment = Adjustment(kind="pergunta", by_rule="CHK-PERGUNTA",
                                         reason="a pergunta registrada já nomeia a solução conhecida: é rotina")
            report.inverted.append(Neutralized(evidence_id=item.id, rule_id="INC-D2", source_id=item.source_id,
                                               by_rule="CHK-PERGUNTA"))


def apply_consistency(results: dict[str, CriterionResult], catalog: Catalog, use_text_markers: bool = False,
                      checks: ChecksReport | None = None, neutralize: bool = True,
                      inc_d2: bool = False) -> ConsistencyReport:
    report = ConsistencyReport()
    if inc_d2:
        _inc_d2_against_known_solution(results, checks, report)
    if not neutralize:
        return report
    reference_rules = {r.id for r in catalog.reference_rules()}
    novelty = results.get("NOV")
    for run in novelty.rules if novelty else []:
        for item in run.evidences:
            if item.polarity != "negativa":
                continue
            if run.rule_id in reference_rules:
                report.reference_sources.setdefault(item.source_id, run.rule_id)
            elif CONTAINMENT_RE.search(item.explanation or ""):
                if use_text_markers:
                    report.reference_sources.setdefault(item.source_id, run.rule_id)
                else:
                    report.warnings.append(f"{item.source_alias} marcada só pelo texto de {run.rule_id} "
                                           "(contenção pela referência anterior): não neutralizada")
    for criterion in NEUTRALIZED:
        result = results.get(criterion)
        for run in result.rules if result else []:
            for item in run.evidences:
                by_rule = report.reference_sources.get(item.source_id)
                if (by_rule is None or item.polarity != "positiva" or item.nature in NUMERIC_NATURES
                        or item.adjustment is not None):
                    continue  # the reference provides the function, not the result of the trial
                item.adjustment = Adjustment(
                    kind="consistencia", by_rule=by_rule,
                    reason=f"a mesma fonte é evidência de {by_rule} de que a referência anterior já fornecia a função")
                report.neutralized.append(Neutralized(evidence_id=item.id, rule_id=run.rule_id,
                                                      source_id=item.source_id, by_rule=by_rule))
    return report
