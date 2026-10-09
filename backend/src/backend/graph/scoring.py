"""Deterministic 0–100 score. An indicator for the analyst only: the class never comes from it."""

from pydantic import BaseModel

from backend.catalog.models import CatalogRule
from backend.criteria.schemas import EvidenceItem, RuleRun


class RuleScore(BaseModel):
    rule_id: str
    status: str
    positive: int
    negative: int
    score: int | None  # None = no evidence (out of the mean), never zero
    in_mean: bool
    counted_evidence_ids: list[str]


def counted_evidences(run: RuleRun) -> list[EvidenceItem]:
    """The same source counts once per rule (first evidence of each source)."""
    seen: set[str] = set()
    counted = []
    for item in run.evidences:
        if item.source_id not in seen:
            seen.add(item.source_id)
            counted.append(item)
    return counted


def score_rule(run: RuleRun, rule: CatalogRule | None) -> RuleScore:
    counted = counted_evidences(run)
    positive = sum(e.polarity == "positiva" for e in counted)
    negative = len(counted) - positive
    total = positive + negative
    return RuleScore(
        rule_id=run.rule_id,
        status=run.status,
        positive=positive,
        negative=negative,
        score=round(100 * positive / total) if total else None,
        in_mean=bool(rule and rule.in_mean),
        counted_evidence_ids=[e.id for e in counted],
    )


def score_criterion(scores: list[RuleScore]) -> int | None:
    values = [s.score for s in scores if s.in_mean and s.score is not None]
    return round(sum(values) / len(values)) if values else None
