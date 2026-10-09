"""Spec 13 — static export of what the front-end consumes, read straight from the database.

`backend-export-frontend` writes `frontend-static/` with one JSON per API route (the same
payloads the routers answer), so the hifi front-end can run without the backend. The
projection is the one the routes use (`project_analysis`, `summarize`, `GraphRead`) — never
a parallel mapping. Read-only export: it never writes a decision or an analysis.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from backend.analyses.models import Analysis
from backend.analyses.schemas import AnalysisStatusRead, GraphEdgeRead, GraphNodeRead, GraphRead
from backend.catalog.models import Catalog
from backend.frontend_api import schemas as fe
from backend.frontend_api.projection import project_analysis
from backend.graph.models import GraphEdge, GraphNode
from backend.projects.models import Project
from backend.projects.router import summarize
from backend.projects.schemas import ProjectRead
from backend.review.models import Contestation, Decision, EvidenceReview, RuleDecision
from backend.review.schemas import ContestationRead, DecisionRead, EvidenceReviewRead, RuleDecisionRead
from backend.users.models import User


class ExportError(RuntimeError):
    pass


class ProjectExport(BaseModel):
    id: str
    code: str | None = None
    name: str
    analysis_id: str | None = None
    files: list[str] = Field(default_factory=list)


class ExportResult(BaseModel):
    folder: str
    projects: list[ProjectExport]
    ok: bool = True


def _dump(model, by_alias: bool = True) -> str:
    if isinstance(model, list):
        return json.dumps([m.model_dump(mode="json", by_alias=by_alias) for m in model], ensure_ascii=False, indent=1)
    return json.dumps(model.model_dump(mode="json", by_alias=by_alias), ensure_ascii=False, indent=1)


def _write(out: Path, rel: str, content: str) -> Path:
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _graph_read(analysis: Analysis) -> GraphRead:
    nodes = await GraphNode.find(GraphNode.analysis_id == str(analysis.id)).to_list()
    edges = await GraphEdge.find(GraphEdge.analysis_id == str(analysis.id)).to_list()
    return GraphRead(
        analysis_id=str(analysis.id),
        nodes=[GraphNodeRead(node_id=n.node_id, kind=n.kind, label=n.label, props=n.props) for n in nodes],
        edges=[GraphEdgeRead(source=e.source, target=e.target, kind=e.kind, props=e.props) for e in edges],
    )


async def _analysis_view(catalog: Catalog, analysis: Analysis, project: Project) -> fe.Analysis | None:
    """The hifi tree, validated: a payload that will not parse is a bug, fail fast (D10)."""
    if analysis.status != "concluida":
        return None
    contestations = await Contestation.find(Contestation.analysis_id == str(analysis.id)).to_list()
    try:
        return fe.Analysis.model_validate(
            project_analysis(catalog, analysis, project, contestations).model_dump(mode="json", by_alias=True)
        )
    except Exception as error:
        raise ExportError(f"análise {analysis.id} não valida contra o contrato do front: {error}") from error


async def _read_models(model, read_cls, project_id: str) -> list:
    rows = await model.find(model.project_id == project_id).to_list()
    rows.sort(key=lambda r: getattr(r, "created_at", None) or getattr(r, "decided_at", None)
             or datetime.min.replace(tzinfo=UTC))
    return [read_cls.model_validate({**row.model_dump(mode="json"), "id": str(row.id)}) for row in rows]


async def export_frontend(out: Path, owner: str | None = None, project: str | None = None,
                          include_benchmark: bool = False, catalog: Catalog | None = None) -> ExportResult:
    """Writes `out` with one JSON per route. Filters: `owner` (analyst) and `project` (single id).

    `include_benchmark`: the default mirrors GET /projects (benchmark runs are hidden from the
    analyst's lists). The static front is the exception: its purpose is to show the analysed
    cases — benchmark projects (the delivery/PRJxx runs) are exactly the demo data — so the
    static export brings them in with this flag."""
    from backend.catalog.loader import get_catalog

    catalog = catalog or get_catalog()
    out.mkdir(parents=True, exist_ok=True)
    routes: dict[str, int] = {}

    query = Project.find(Project.benchmark_id == None)  # noqa: E711 — hidden from the analyst's lists (D6)
    if include_benchmark:
        query = Project.find_all()
    if owner:
        query = query.find(Project.owner_id == owner)
    if project:
        query = query.find(Project.id == PydanticObjectId(project))
    projects = await query.sort(+Project.created_at).to_list()
    if project and not projects:
        raise ExportError(f"projeto {project} não encontrado (ou é de benchmark)")

    exported: list[ProjectExport] = []
    for proj in projects:
        pid = str(proj.id)
        analyses = await Analysis.find(Analysis.project_id == pid).sort(-Analysis.version).to_list()
        latest = next((a for a in analyses if a.status == "concluida"), None)
        view = await _analysis_view(catalog, latest, proj) if latest else None

        _write(out, f"{pid}/project.json", _dump(ProjectRead.of(proj)))
        routes["GET /projects/{id}"] = routes.get("GET /projects/{id}", 0) + 1
        if view is not None and not isinstance(view, fe.Analysis):  # fail fast (D10)
            raise ExportError(f"payload de GET /projects/{pid}/analyses inválido ({pid}/analyses.json)")
        _write(out, f"{pid}/analyses.json", _dump([view]) if view else "null")
        routes["GET /projects/{id}/analyses"] = routes.get("GET /projects/{id}/analyses", 0) + 1

        decisions = await _read_models(Decision, DecisionRead, pid)
        _write(out, f"{pid}/decisions.json", _dump(decisions))
        contestations = await _read_models(Contestation, ContestationRead, pid)
        _write(out, f"{pid}/contestations.json", _dump(contestations))
        rule_decisions = await _read_models(RuleDecision, RuleDecisionRead, pid)
        _write(out, f"{pid}/rule-decisions.json", _dump(rule_decisions))
        evidence_reviews = await _read_models(EvidenceReview, EvidenceReviewRead, pid)
        _write(out, f"{pid}/evidence-reviews.json", _dump(evidence_reviews))

        for analysis in analyses:
            aid = str(analysis.id)
            folder = f"{pid}/analysis/{aid}"
            _write(out, f"{folder}/status.json", _dump(AnalysisStatusRead.of(analysis)))
            routes["GET /analyses/{id}/status"] = routes.get("GET /analyses/{id}/status", 0) + 1
            graph = await _graph_read(analysis)
            try:
                GraphRead.model_validate(graph.model_dump(mode="json", by_alias=True))
            except Exception as error:
                raise ExportError(f"grafo da análise {aid} não valida ({error})") from error
            _write(out, f"{folder}/graph.json", _dump(graph))
            routes["GET /analyses/{id}/graph"] = routes.get("GET /analyses/{id}/graph", 0) + 1
            if analysis.report is not None:  # a failed stage is absent, never a phantom report (D8)
                _write(out, f"{folder}/report.json",
                       json.dumps(analysis.report, ensure_ascii=False, indent=1))
                routes["GET /analyses/{id}/report.json"] = routes.get("GET /analyses/{id}/report.json", 0) + 1

        exported.append(ProjectExport(id=pid, code=proj.code, name=proj.name,
                                      analysis_id=str(latest.id) if latest else None,
                                      files=[f"{pid}/analyses.json", f"{pid}/project.json"]))

    # users for the front's mock login: seed-like entries, never a hash (D4)
    users = [{"id": str(u.id), "name": u.name, "email": str(u.email)}
             for u in await User.find_all().to_list()]
    _write(out, "users.json", json.dumps(users, ensure_ascii=False, indent=1))

    summaries = [await summarize(proj) for proj in projects]
    page = {"items": [s.model_dump(mode="json", by_alias=True) for s in summaries],
            "total": len(summaries), "page": 1, "pageSize": len(summaries),
            "statusCounts": {status: sum(1 for s in summaries if s.status == status)
                             for status in ("processing", "ready", "decided", "error")}}
    _write(out, "projects.json", json.dumps(page, ensure_ascii=False, indent=1))
    routes["GET /projects"] = 1

    manifest = {
        "geradoEm": datetime.now(UTC).isoformat(), "projects": len(exported),
        "routes": routes, "catalogVersion": catalog.versao,
        "models": {role: model for role, model in _role_models().items()},
        "files": {p.relative_to(out).as_posix(): _sha256(p)
                  for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"},
    }
    _write(out, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    return ExportResult(folder=str(out), projects=exported)


def _role_models() -> dict[str, str]:
    from backend.config import settings

    roles = {"default": settings.ollama_model}
    for role in ("extraction", "doc", "search", "judge", "report", "chat"):
        model = getattr(settings, f"ollama_model_{role}", None)
        if model:
            roles[role] = model
    return roles