import uuid
from datetime import UTC, datetime
from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(BaseModel):
    job_id: str
    kind: str
    status: JobStatus = JobStatus.PENDING
    progress: dict[str, str] = Field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class JobStore:
    """Jobs em memória: somem quando o processo reinicia (suficiente para a demo)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, kind: str, steps: list[str]) -> Job:
        job = Job(job_id=uuid.uuid4().hex, kind=kind, progress={step: JobStatus.PENDING for step in steps})
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def set_step(self, job_id: str, step: str, status: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        job.progress[step] = status

    def finish(self, job_id: str, result: Any) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.DONE
        job.result = result
        job.finished_at = datetime.now(UTC)

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.FAILED
        job.error = error
        job.progress = {step: "failed" if state == "running" else state for step, state in job.progress.items()}
        job.finished_at = datetime.now(UTC)


@lru_cache
def get_job_store() -> JobStore:
    return JobStore()
