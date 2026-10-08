import uuid
from datetime import UTC, datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field

ProjectStatus = Literal["processing", "ready", "decided", "error"]


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class ProjectFile(BaseModel):
    id: str = Field(default_factory=lambda: new_id("doc"))
    file_name: str  # relative path inside the package
    mime_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=now)
    sha256: str
    gridfs_id: str
    superseded_at: datetime | None = None
    superseded_by: str | None = None


class Project(Document):
    owner_id: str
    name: str
    company: str | None = None
    free_text: str | None = None
    code: str | None = None
    created_at: datetime = Field(default_factory=now)
    status: ProjectStatus = "processing"
    documents: list[ProjectFile] = Field(default_factory=list)
    latest_analysis_id: str | None = None
    benchmark_id: str | None = None  # created by a benchmark run: hidden from the analyst's lists

    class Settings:
        name = "projects"

    def active_documents(self) -> list[ProjectFile]:
        return [doc for doc in self.documents if doc.superseded_at is None]
