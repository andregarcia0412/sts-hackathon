from datetime import datetime
from typing import Any

from backend.analyses.models import Analysis, AnalysisVersions, Stage
from backend.api_schema import CamelModel
from backend.llm.usage import LLMUsage


class StageRead(CamelModel):
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_s: float | None = None
    error: str | None = None


class VersionsRead(CamelModel):
    schema_version: str | None = None
    catalog_version: str | None = None
    models: dict[str, str | None] = {}
    prompts: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    temperature: float = 0


class AnalysisStatusRead(CamelModel):
    id: str
    project_id: str
    version: int
    previous_analysis_id: str | None = None
    batch_id: str | None = None
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_s: float | None = None
    stages: list[StageRead]
    suggested_class: str | None = None
    inconsistent: bool | None = None
    error: str | None = None
    versions: VersionsRead
    usage: LLMUsage | None = None

    @classmethod
    def of(cls, analysis: Analysis) -> "AnalysisStatusRead":
        return cls(
            id=str(analysis.id),
            project_id=analysis.project_id,
            version=analysis.version,
            previous_analysis_id=analysis.previous_analysis_id,
            batch_id=analysis.batch_id,
            status=analysis.status,
            created_at=analysis.created_at,
            started_at=analysis.started_at,
            finished_at=analysis.finished_at,
            total_s=analysis.total_s,
            stages=[StageRead.model_validate(s.model_dump()) for s in analysis.stages],
            suggested_class=analysis.suggestion.suggested_class if analysis.suggestion else None,
            inconsistent=analysis.suggestion.inconsistent if analysis.suggestion else None,
            error=analysis.error,
            versions=VersionsRead.model_validate(analysis.versions.model_dump()),
            usage=analysis.usage,
        )


class GraphNodeRead(CamelModel):
    node_id: str
    kind: str
    label: str
    props: dict[str, Any]


class GraphEdgeRead(CamelModel):
    source: str
    target: str
    kind: str
    props: dict[str, Any]


class GraphRead(CamelModel):
    analysis_id: str
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]


class BatchRequest(CamelModel):
    package_dir: str
    name: str | None = None


class BatchItem(CamelModel):
    project_id: str
    project_name: str
    code: str | None = None
    analysis_id: str | None = None
    status: str
    suggested_class: str | None = None
    inconsistent: bool | None = None
    total_s: float | None = None
    current_stage: str | None = None


class BatchRead(CamelModel):
    id: str
    name: str
    created_at: datetime
    total: int
    counts: dict[str, int]
    items: list[BatchItem] = []
    errors: list[str] = []


__all__ = ["AnalysisStatusRead", "AnalysisVersions", "BatchItem", "BatchRead", "BatchRequest", "GraphRead", "Stage"]
