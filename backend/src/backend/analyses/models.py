from datetime import date, datetime
from typing import Any, Literal

from beanie import Document
from pydantic import BaseModel, Field

from backend.criteria.schemas import CriterionResult
from backend.extraction.schema import CanonicalProject
from backend.graph.classify import ClassSuggestion
from backend.graph.scoring import RuleScore
from backend.graph.states import CriterionState
from backend.llm.usage import LLMUsage
from backend.projects.models import now

StageStatus = Literal["pendente", "rodando", "concluida", "falhou", "nao_executada"]
AnalysisStatus = Literal["pendente", "rodando", "concluida", "falhou"]


class Stage(BaseModel):
    name: str
    status: StageStatus = "pendente"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_s: float | None = None
    error: str | None = None


class AnalysisVersions(BaseModel):
    """Everything needed to explain (and reproduce) an analysis years later (principle 11)."""

    schema_version: str | None = None
    catalog_version: str | None = None
    models: dict[str, str | None] = Field(default_factory=dict)
    prompts: dict[str, str] = Field(default_factory=dict)
    file_hashes: dict[str, str] = Field(default_factory=dict)
    temperature: float = 0


class Analysis(Document):
    project_id: str
    owner_id: str
    version: int
    previous_analysis_id: str | None = None
    batch_id: str | None = None
    status: AnalysisStatus = "pendente"
    created_at: datetime = Field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_s: float | None = None
    stages: list[Stage] = Field(default_factory=list)
    reference_date_override: date | None = None
    versions: AnalysisVersions = Field(default_factory=AnalysisVersions)
    criteria: dict[str, CriterionResult] = Field(default_factory=dict)
    scores: dict[str, list[RuleScore]] = Field(default_factory=dict)
    criterion_scores: dict[str, int | None] = Field(default_factory=dict)
    states: dict[str, CriterionState] = Field(default_factory=dict)
    suggestion: ClassSuggestion | None = None
    report: dict[str, Any] | None = None
    usage: LLMUsage | None = None  # LLM calls, tokens and time per role
    error: str | None = None

    class Settings:
        name = "analyses"

    def stage(self, name: str) -> Stage:
        return next(s for s in self.stages if s.name == name)


class CanonicalRecord(Document):
    """Canonical JSON of the analysed package, saved with the analysis that used it."""

    analysis_id: str
    canonical: CanonicalProject

    class Settings:
        name = "canonical_projects"


class Batch(Document):
    owner_id: str
    name: str
    created_at: datetime = Field(default_factory=now)
    project_ids: list[str] = Field(default_factory=list)
    analysis_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    benchmark_id: str | None = None

    class Settings:
        name = "batches"
