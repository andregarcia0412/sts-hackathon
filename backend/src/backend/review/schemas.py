from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from backend.api_schema import CamelModel
from backend.review.models import ContestationReason, DecisionOutcome, RuleRating


class RuleOverrideIn(CamelModel):
    rule_id: str
    note: str
    analysis_id: str | None = None


class DecisionIn(CamelModel):
    project_id: str
    analysis_id: str
    analysis_ids: list[str] = []
    outcome: DecisionOutcome
    justification: str
    analyst_name: str
    rule_overrides: list[RuleOverrideIn] = []

    @field_validator("justification", "analyst_name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required")
        return value.strip()


class DecisionRead(DecisionIn):
    id: str
    decided_at: datetime
    suggested_class: str | None = None


class AnalysisChangeOut(CamelModel):
    node_id: str
    node_label: str
    field: str
    before: int | float | str | None
    after: int | float | str | None


class ResolutionOut(CamelModel):
    verdict: Literal["accepted", "maintained"]
    explanation: str
    changes: list[AnalysisChangeOut]
    resolved_at: datetime


class ContestationIn(CamelModel):
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    reason: ContestationReason
    argument: str = Field(min_length=1)
    suggested_score: float | None = None
    suggested_polarity: Literal["positive", "negative"] | None = None
    author: str


class ContestationRead(ContestationIn):
    id: str
    status: Literal["open", "resolved"]
    resolution: ResolutionOut | None = None
    created_at: datetime


class RuleDecisionIn(CamelModel):
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    rating: RuleRating
    suggested: RuleRating | None = None
    justification: str
    author: str


class RuleDecisionRead(RuleDecisionIn):
    id: str
    created_at: datetime


class EvidenceReviewIn(CamelModel):
    project_id: str
    analysis_id: str
    node_id: str
    node_label: str
    verdict: Literal["confirmed", "discarded"]
    note: str | None = None
    author: str


class EvidenceReviewRead(EvidenceReviewIn):
    id: str
    created_at: datetime
