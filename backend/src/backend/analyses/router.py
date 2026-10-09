from typing import Annotated, Literal

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.analyses.batch import batch_panel, groups_from_directory, groups_from_zip_files, import_projects
from backend.analyses.deps import Runner, Service, inside_package_dir, owned_analysis, start_analysis
from backend.analyses.models import Analysis, Batch, CanonicalRecord
from backend.analyses.schemas import AnalysisStatusRead, BatchRead, BatchRequest, GraphEdgeRead, GraphNodeRead, GraphRead
from backend.auth.dependencies import CurrentUser
from backend.extraction.schema import CanonicalProject
from backend.graph.decision import decision_graph
from backend.graph.models import GraphEdge, GraphNode
from backend.graph.queries import trace
from backend.projects.importer import ImportError_, files_from_zip
from backend.projects.router import owned_or_404

router = APIRouter(tags=["analyses"])


@router.post("/projects/{project_id}/analyses", status_code=status.HTTP_202_ACCEPTED)
async def reanalyze(project_id: str, user: CurrentUser, service: Service, runner: Runner) -> AnalysisStatusRead:
    project = await owned_or_404(project_id, user)
    return AnalysisStatusRead.of(await start_analysis(project, service, runner))


@router.get("/projects/{project_id}/analyses/history")
async def history(project_id: str, user: CurrentUser) -> list[AnalysisStatusRead]:
    project = await owned_or_404(project_id, user)
    analyses = await Analysis.find(Analysis.project_id == str(project.id)).sort(-Analysis.version).to_list()
    return [AnalysisStatusRead.of(a) for a in analyses]


@router.get("/analyses/{analysis_id}/status")
async def analysis_status(analysis_id: str, user: CurrentUser) -> AnalysisStatusRead:
    return AnalysisStatusRead.of(await owned_analysis(analysis_id, str(user.id)))


@router.get("/analyses/{analysis_id}/graph")
async def graph(analysis_id: str, user: CurrentUser, view: Literal["completo", "decisao"] = "completo") -> GraphRead:
    """`view=decisao`: only the decision path (class → criteria → answers → evidence → cited fragment), for the
    analyst; the default is the full graph (audit: searches, every rule, the rows used by the checks)."""
    analysis = await owned_analysis(analysis_id, str(user.id))
    nodes = await GraphNode.find(GraphNode.analysis_id == str(analysis.id)).to_list()
    edges = await GraphEdge.find(GraphEdge.analysis_id == str(analysis.id)).to_list()
    if view == "decisao":
        nodes, edges = decision_graph(nodes, edges)
    return GraphRead(
        analysis_id=str(analysis.id),
        nodes=[GraphNodeRead(node_id=n.node_id, kind=n.kind, label=n.label, props=n.props) for n in nodes],
        edges=[GraphEdgeRead(source=e.source, target=e.target, kind=e.kind, props=e.props) for e in edges],
    )


@router.get("/analyses/{analysis_id}/graph/trace/{node_id:path}")
async def graph_trace(analysis_id: str, node_id: str, user: CurrentUser) -> list[GraphNodeRead]:
    analysis = await owned_analysis(analysis_id, str(user.id))
    return [GraphNodeRead(node_id=n.node_id, kind=n.kind, label=n.label, props=n.props)
            for n in await trace(str(analysis.id), node_id)]


@router.get("/analyses/{analysis_id}/canonical", response_model_by_alias=True)
async def canonical(analysis_id: str, user: CurrentUser):
    analysis = await owned_analysis(analysis_id, str(user.id))
    record = await CanonicalRecord.find_one(CanonicalRecord.analysis_id == str(analysis.id))
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Canonical JSON not available (extraction did not finish)")
    return _camel(record.canonical)


def _camel(canonical: CanonicalProject) -> dict:
    from pydantic.alias_generators import to_camel

    def convert(value):
        if isinstance(value, dict):
            return {to_camel(k) if "_" in k and not k.isupper() else k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    data = canonical.model_dump(mode="json")
    fragments = data.pop("fragments")
    converted = convert(data)
    # fragment `data` keeps the original column names of the package
    converted["fragments"] = [{**convert({k: v for k, v in f.items() if k != "data"}), "data": f["data"]} for f in fragments]
    return converted


@router.post("/batches", status_code=status.HTTP_202_ACCEPTED)
async def create_batch(body: BatchRequest, user: CurrentUser, service: Service, runner: Runner) -> BatchRead:
    root = inside_package_dir(body.package_dir)
    groups = groups_from_directory(root)
    if not groups:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No project folder found (no evidence inventory)")
    batch = await import_projects(groups, str(user.id), body.name or root.name, service, runner)
    return await batch_panel(batch)


@router.post("/batches/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_batch(user: CurrentUser, service: Service, runner: Runner,
                       file: Annotated[UploadFile, File()]) -> BatchRead:
    try:
        files = files_from_zip(await file.read())
    except ImportError_ as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    groups = groups_from_zip_files(files)
    if not groups:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No project folder found (no evidence inventory)")
    batch = await import_projects(groups, str(user.id), file.filename or "lote", service, runner)
    return await batch_panel(batch)


@router.get("/batches")
async def list_batches(user: CurrentUser) -> list[BatchRead]:
    batches = await Batch.find(Batch.owner_id == str(user.id), Batch.benchmark_id == None).sort(-Batch.created_at).to_list()  # noqa: E711
    return [await batch_panel(b) for b in batches]


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, user: CurrentUser) -> BatchRead:
    try:
        batch = await Batch.get(PydanticObjectId(batch_id))
    except (InvalidId, TypeError):
        batch = None
    if batch is None or batch.owner_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Batch not found")
    return await batch_panel(batch)
