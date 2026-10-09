from pathlib import Path
from typing import Annotated

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status

from backend.analyses.jobs import InlineRunner, JobRunner
from backend.analyses.models import Analysis
from backend.analyses.orchestrator import AnalysisService
from backend.config import settings
from backend.projects.models import Project


def get_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def get_runner(request: Request) -> JobRunner | InlineRunner:
    return request.app.state.runner


Service = Annotated[AnalysisService, Depends(get_service)]
Runner = Annotated[JobRunner | InlineRunner, Depends(get_runner)]


async def start_analysis(project: Project, service: AnalysisService, runner, batch_id: str | None = None) -> Analysis:
    """Creates the analysis and returns at once; processing runs in the background."""
    analysis = await service.create(project, batch_id=batch_id)
    analysis_id = str(analysis.id)
    await runner.submit(lambda: service.run(analysis_id))
    return await Analysis.get(analysis.id)


async def owned_analysis(analysis_id: str, owner_id: str) -> Analysis:
    try:
        analysis = await Analysis.get(PydanticObjectId(analysis_id))
    except (InvalidId, TypeError):
        analysis = None
    if analysis is None or analysis.owner_id != owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return analysis


def inside_package_dir(path: str | Path, file: bool = False) -> Path:
    """A folder (or file) of the challenge package; relative paths are relative to PACKAGE_DIR."""
    if settings.package_dir is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "PACKAGE_DIR is not configured on the server")
    root = Path(settings.package_dir).resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"{path} must be inside PACKAGE_DIR")
    if not (target.is_file() if file else target.is_dir()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{path} not found")
    return target
