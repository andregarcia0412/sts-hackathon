"""Analyst review: every record is append-only (who, when, why) and never erases the system suggestion (T7)."""

from datetime import datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field

from backend.criteria.schemas import EvidenceItem
from backend.projects.models import now

DecisionOutcome = Literal["eligible", "eligible_with_caveats", "not_eligible", "insufficient_evidence"]
ContestationReason = Literal["polarity", "score_too_high", "score_too_low", "wrong_excerpt", "missing_evidence", "other"]
RuleRating = Literal["sustained", "partial", "contradictory", "not_sustained", "needs_expert"]


class RuleOverride(BaseModel):
    rule_id: str
    note: str
    analysis_id: str | None = None


class Decision(Document):
    project_id: str
    analysis_id: str
    analysis_ids: list[str] = Field(default_factory=list)
    outcome: DecisionOutcome
    justification: str
    analyst_name: str
    analyst_id: str
    decided_at: datetime = Field(default_factory=now)
    rule_overrides: list[RuleOverride] = Field(default_factory=list)
    suggested_class: str | None = None  # snapshot of the system suggestion at decision time

    class Settings:
        name = "decisions"


class AnalysisChange(BaseModel):
    node_id: str
    node_label: str
    field: Literal["score", "polarity", "state"]
    before: int | float | str | None
    after: int | float | str | None


class ContestationResolution(BaseModel):
    verdict: Literal["accepted", "maintained"]
    explanation: str
    changes: list[AnalysisChange] = Field(default_factory=list)
    resolved_at: datetime = Field(default_factory=now)
    # extensions: how the accepted change is applied on top of the (untouched) analysis
    added_evidences: list[EvidenceItem] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)
    flipped_evidence_ids: list[str] = Field(default_factory=list)
    new_state: str | None = None
    criterion: str | None = None


class Contestation(Document):
    status: Literal["open", "resolved"] = "open"
    resolution: ContestationResolution | None = None
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    reason: ContestationReason
    argument: str
    suggested_score: float | None = None
    suggested_polarity: Literal["positive", "negative"] | None = None
    author: str
    author_id: str
    created_at: datetime = Field(default_factory=now)

    class Settings:
        name = "contestations"


class RuleDecision(Document):
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    rating: RuleRating
    suggested: RuleRating | None = None
    justification: str
    author: str
    author_id: str
    created_at: datetime = Field(default_factory=now)

    class Settings:
        name = "rule_decisions"


class EvidenceReview(Document):
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    verdict: Literal["confirmed", "discarded"]
    note: str | None = None
    author: str
    author_id: str
    created_at: datetime = Field(default_factory=now)

    class Settings:
        name = "evidence_reviews"
