from typing import Annotated

from datetime import date

from pydantic import ValidationError
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status

from backend.auth.dependencies import CurrentUser
from backend.projects.importer import ImportError_, IncomingFile, files_from_zip
from backend.projects.models import Project
from backend.frontend_api.project_query import ProjectQuery, apply_project_query
from backend.projects.schemas import ProjectPage, ProjectRead, ProjectSummary
from backend.projects.service import add_documents, create_project, get_owned_project

router = APIRouter(prefix="/projects", tags=["projects"])


async def read_uploads(uploads: list[UploadFile]) -> list[IncomingFile]:
    files: list[IncomingFile] = []
    for upload in uploads:
        data = await upload.read()
        name = upload.filename or "arquivo"
        if name.lower().endswith(".zip"):
            try:
                files += files_from_zip(data)
            except ImportError_ as error:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
        else:
            files.append(IncomingFile(path=name.replace("\\", "/").lstrip("/"), data=data))
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "At least one file is required")
    return files


async def owned_or_404(project_id: str, user) -> Project:
    project = await get_owned_project(project_id, str(user.id))
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    user: CurrentUser,
    request: Request,
    name: Annotated[str, Form(min_length=1)],
    files: Annotated[list[UploadFile], File()] = [],  # noqa: B006
    company: Annotated[str | None, Form()] = None,
    freeText: Annotated[str | None, Form()] = None,  # noqa: N803  (front-end field name)
) -> ProjectRead:
    incoming = await read_uploads(files)
    project = await create_project(str(user.id), name, incoming, company=company, free_text=freeText)
    await _start(request, project)
    return ProjectRead.of(await Project.get(project.id))


@router.get("")
async def list_projects(
    user: CurrentUser,
    search: str | None = None,
    statuses: Annotated[list[str], Query()] = [],  # noqa: B006
    weakestBand: str | None = None,  # noqa: N803
    outcome: str | None = None,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    sort: str = "recent",
    page: int = 1,
    pageSize: int = 20,  # noqa: N803
) -> ProjectPage:
    try:
        query = ProjectQuery(
            search=search,
            statuses=statuses,
            weakest_band=weakestBand,
            outcome=outcome,
            date_from=from_,
            date_to=to,
            sort=sort,
            page=page,
            page_size=pageSize,
        )
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.errors(include_url=False))
    projects = await Project.find(Project.owner_id == str(user.id), Project.benchmark_id == None).to_list()  # noqa: E711
    summaries = [await summarize(project) for project in projects]
    return apply_project_query(summaries, query)


async def summarize(project: Project) -> ProjectSummary:
    from backend.analyses.models import Analysis
    from backend.catalog.loader import get_catalog
    from backend.catalog.models import CRITERIA_ORDER
    from backend.projects.schemas import CriterionScoreSummary, LastDecision
    from backend.review.models import Contestation, Decision

    summary = ProjectSummary(**ProjectRead.of(project).model_dump())
    analysis = await Analysis.find(
        Analysis.project_id == str(project.id), Analysis.status == "concluida"
    ).sort(-Analysis.version).first_or_none()
    if analysis:
        catalog = get_catalog()
        summary.frameworks = ["frascati"]
        summary.score_summary = [
            CriterionScoreSummary(criterion_key=catalog.criteria[c].chave, name=catalog.criteria[c].nome,
                                  score=analysis.criterion_scores.get(c))
            for c in CRITERIA_ORDER
        ]
        summary.suggested_class = analysis.suggestion.suggested_class if analysis.suggestion else None
    last = await Decision.find(Decision.project_id == str(project.id)).sort(-Decision.decided_at).first_or_none()
    if last:
        summary.last_decision = LastDecision(outcome=last.outcome, decided_at=last.decided_at, analyst_name=last.analyst_name)
    contestations = await Contestation.find(Contestation.project_id == str(project.id)).to_list()
    summary.contestation_count = len(contestations)
    summary.open_contestation_count = sum(c.status == "open" for c in contestations)
    return summary


@router.get("/{project_id}")
async def get(project_id: str, user: CurrentUser) -> ProjectRead:
    return ProjectRead.of(await owned_or_404(project_id, user))


@router.post("/{project_id}/documents")
async def add(
    project_id: str, user: CurrentUser, request: Request, files: Annotated[list[UploadFile], File()]
) -> ProjectRead:
    """Including or replacing a file triggers a full re-analysis (a new version; the old one is kept)."""
    project = await owned_or_404(project_id, user)
    project = await add_documents(project, await read_uploads(files))
    await _start(request, project)
    return ProjectRead.of(await Project.get(project.id))


async def _start(request: Request, project: Project) -> None:
    from backend.analyses.deps import start_analysis

    await start_analysis(project, request.app.state.analysis_service, request.app.state.runner)
