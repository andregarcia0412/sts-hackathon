"""Shapes of frontend/src/domain/types.ts (feature/frontend-hifi) plus documented domain extensions."""

from datetime import date, datetime
from typing import Literal

from backend.api_schema import CamelModel


class Reference(CamelModel):
    label: str
    citation: str | None = None
    url: str | None = None


class ProjectExcerpt(CamelModel):
    document_id: str | None = None
    file_name: str | None = None
    page: int | None = None
    excerpt: str


class EvidenceSource(CamelModel):  # extension
    origin: Literal["doc", "web"]
    fragment_id: str | None = None
    alias: str
    nature: str
    url: str | None = None
    published_date: date | None = None
    captured_at: datetime | None = None
    query: str | None = None


class Evidence(CamelModel):
    id: str
    title: str
    polarity: Literal["positive", "negative"]
    explanation: str
    project_excerpt: ProjectExcerpt | None = None
    references: list[Reference] = []
    # extensions
    rule_code: str
    source: EvidenceSource
    counted: bool = True
    adjusted: bool = False


class ScoreFactor(CamelModel):
    kind: Literal["evidence", "rule", "adjustment"]
    ref_id: str | None = None
    label: str
    points: int
    value: float | None = None
    weight: float | None = None


class ScoreExplanation(CamelModel):
    method: str
    baseline: int
    factors: list[ScoreFactor]


class Counts(CamelModel):
    positive: int
    negative: int


class Rule(CamelModel):
    id: str
    code: str
    name: str
    score: int | None  # extension: null = no evidence (never zero)
    explanation: str
    normative_source: Reference
    evidences: list[Evidence]
    score_explanation: ScoreExplanation | None = None
    # extensions
    counts: Counts
    status: str
    status_reason: str | None = None
    in_mean: bool
    block: str
    normative_sources: list[str] = []


class Criterion(CamelModel):
    id: str
    key: str
    name: str
    score: int | None
    summary: str
    rules: list[Rule]
    score_explanation: ScoreExplanation | None = None
    # extensions
    criterion_id: str
    state: str | None = None
    column: str | None = None
    llm_state: str | None = None
    gates: list[str] = []
    normative_source: str
    decisive_evidence_ids: list[str] = []


class AnalysisChangeRead(CamelModel):
    node_id: str
    node_label: str
    field: str
    before: int | float | str | None
    after: int | float | str | None
    contestation_id: str | None = None


class Caveat(CamelModel):
    scope: str | None = None
    limitation: str | None = None
    evidence_needed: str | None = None


class MissingLink(CamelModel):
    link: str | None = None
    evidence_to_request: list[str] = []


class DivergenceRead(CamelModel):
    criterion_key: str
    statement: str
    testimony_fragment_id: str
    record_fragment_id: str
    record_alias: str


class GapRead(CamelModel):
    rule_code: str
    status: str
    reason: str


class VersionsRead(CamelModel):
    schema_version: str | None = None
    catalog_version: str | None = None
    models: dict[str, str | None] = {}
    prompts: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    temperature: float = 0


class Analysis(CamelModel):
    id: str
    project_id: str
    framework: Literal["frascati"] = "frascati"
    generated_at: datetime | None
    criteria: list[Criterion]
    adjustments: list[AnalysisChangeRead] = []
    # extensions
    version: int
    status: str
    suggested_class: str | None = None
    inconsistent: bool = False
    class_reason: str | None = None
    decision_path: list[str] = []
    incomplete: list[str] = []
    caveat: Caveat | None = None
    missing_link: MissingLink | None = None
    divergences: list[DivergenceRead] = []
    missing_links: list[str] = []
    gaps: list[GapRead] = []
    versions: VersionsRead
