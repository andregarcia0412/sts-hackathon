from datetime import datetime

from backend.api_schema import CamelModel
from backend.projects.models import Project, ProjectFile, ProjectStatus


class ProjectDocumentRead(CamelModel):
    id: str
    file_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    sha256: str

    @classmethod
    def of(cls, doc: ProjectFile) -> "ProjectDocumentRead":
        return cls.model_validate(doc.model_dump())


class ProjectRead(CamelModel):
    id: str
    owner_id: str
    name: str
    company: str | None = None
    created_at: datetime
    status: ProjectStatus
    documents: list[ProjectDocumentRead]
    free_text: str | None = None
    # extensions
    code: str | None = None
    superseded_documents: list[ProjectDocumentRead] = []
    latest_analysis_id: str | None = None

    @classmethod
    def of(cls, project: Project) -> "ProjectRead":
        return cls(
            id=str(project.id),
            owner_id=project.owner_id,
            name=project.name,
            company=project.company,
            created_at=project.created_at,
            status=project.status,
            documents=[ProjectDocumentRead.of(d) for d in project.active_documents()],
            free_text=project.free_text,
            code=project.code,
            superseded_documents=[ProjectDocumentRead.of(d) for d in project.documents if d.superseded_at],
            latest_analysis_id=project.latest_analysis_id,
        )


class CriterionScoreSummary(CamelModel):
    criterion_key: str
    name: str
    score: float | None


class LastDecision(CamelModel):
    outcome: str
    decided_at: datetime
    analyst_name: str


class ProjectSummary(ProjectRead):
    score_summary: list[CriterionScoreSummary] | None = None
    frameworks: list[str] = []
    last_decision: LastDecision | None = None
    contestation_count: int = 0
    open_contestation_count: int = 0
    # extensions
    suggested_class: str | None = None


class ProjectPage(CamelModel):
    items: list[ProjectSummary]
    total: int
    page: int
    page_size: int
    status_counts: dict[ProjectStatus, int]
