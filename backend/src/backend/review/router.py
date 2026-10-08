from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status

from backend.analyses.deps import Service, owned_analysis
from backend.analyses.models import Analysis
from backend.auth.dependencies import CurrentUser
from backend.catalog.loader import get_catalog
from backend.errors import safe_error_message
from backend.frontend_api.projection import project_analysis
from backend.frontend_api.schemas import Analysis as AnalysisView
from backend.graph.builder import CLASS_NODE
from backend.graph.models import GraphEdge, GraphNode
from backend.projects.models import Project
from backend.projects.router import owned_or_404
from backend.review.models import Contestation, Decision, EvidenceReview, RuleDecision, RuleOverride
from backend.review.reanalysis import ContestationError, reanalyze
from backend.review.schemas import (
    ContestationIn,
    ContestationRead,
    DecisionIn,
    DecisionRead,
    EvidenceReviewIn,
    EvidenceReviewRead,
    RuleDecisionIn,
    RuleDecisionRead,
)

router = APIRouter(tags=["review"])


def _read(model, doc, **extra):
    return model.model_validate({**doc.model_dump(exclude={"id", "revision_id"}), "id": str(doc.id), **extra})


async def _analysis_of(project: Project, analysis_id: str, user) -> Analysis:
    analysis = await owned_analysis(analysis_id, str(user.id))
    if analysis.project_id != str(project.id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "analysisId does not belong to this project")
    return analysis


@router.get("/projects/{project_id}/analyses")
async def list_analyses(project_id: str, user: CurrentUser) -> list[AnalysisView] | None:
    """Latest finished analysis (the front-end shows one per method). null while nothing has finished."""
    project = await owned_or_404(project_id, user)
    analysis = await Analysis.find(
        Analysis.project_id == str(project.id), Analysis.status == "concluida"
    ).sort(-Analysis.version).first_or_none()
    if analysis is None:
        return None
    contestations = await Contestation.find(Contestation.analysis_id == str(analysis.id)).sort(+Contestation.created_at).to_list()
    return [project_analysis(get_catalog(), analysis, project, contestations)]


@router.get("/projects/{project_id}/decisions")
async def list_decisions(project_id: str, user: CurrentUser) -> list[DecisionRead]:
    project = await owned_or_404(project_id, user)
    decisions = await Decision.find(Decision.project_id == str(project.id)).sort(+Decision.decided_at).to_list()
    return [_read(DecisionRead, d) for d in decisions]


@router.post("/projects/{project_id}/decisions", status_code=status.HTTP_201_CREATED)
async def create_decision(project_id: str, body: DecisionIn, user: CurrentUser) -> DecisionRead:
    project = await owned_or_404(project_id, user)
    analysis = await _analysis_of(project, body.analysis_id, user)
    decision = Decision(
        project_id=str(project.id),
        analysis_id=body.analysis_id,
        analysis_ids=body.analysis_ids or [body.analysis_id],
        outcome=body.outcome,
        justification=body.justification,
        analyst_name=body.analyst_name,
        analyst_id=str(user.id),
        rule_overrides=[RuleOverride(**o.model_dump(by_alias=False)) for o in body.rule_overrides],
        suggested_class=analysis.suggestion.suggested_class if analysis.suggestion else None,
    )
    await decision.insert()
    node_id = f"decision:{decision.id}"
    await GraphNode(analysis_id=str(analysis.id), node_id=node_id, kind="decision", label=f"Decisão: {decision.outcome}",
                    props={"outcome": decision.outcome, "justification": decision.justification,
                           "analyst_name": decision.analyst_name, "analyst_id": decision.analyst_id,
                           "decided_at": decision.decided_at.isoformat(),
                           "suggested_class": decision.suggested_class}).insert()
    await GraphEdge(analysis_id=str(analysis.id), source=node_id, target=CLASS_NODE, kind="decidiu").insert()
    project.status = "decided"
    await project.save()
    return _read(DecisionRead, decision)


@router.get("/projects/{project_id}/contestations")
async def list_contestations(project_id: str, user: CurrentUser) -> list[ContestationRead]:
    project = await owned_or_404(project_id, user)
    items = await Contestation.find(Contestation.project_id == str(project.id)).sort(+Contestation.created_at).to_list()
    return [_read(ContestationRead, c) for c in items]


@router.post("/projects/{project_id}/contestations", status_code=status.HTTP_201_CREATED)
async def create_contestation(project_id: str, body: ContestationIn, user: CurrentUser) -> ContestationRead:
    project = await owned_or_404(project_id, user)
    await _analysis_of(project, body.analysis_id, user)
    contestation = Contestation(**body.model_dump(exclude={"project_id"}, by_alias=False), project_id=str(project.id), author_id=str(user.id))
    await contestation.insert()
    return _read(ContestationRead, contestation)


@router.post("/contestations/{contestation_id}/reanalysis")
async def request_reanalysis(contestation_id: str, user: CurrentUser, service: Service) -> ContestationRead:
    try:
        contestation = await Contestation.get(PydanticObjectId(contestation_id))
    except (InvalidId, TypeError):
        contestation = None
    if contestation is None or contestation.author_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contestation not found")
    if contestation.status == "resolved":
        return _read(ContestationRead, contestation)
    try:
        resolution = await reanalyze(service, contestation)
    except ContestationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    except Exception as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"reanálise falhou: {safe_error_message(error)}")
    contestation.status, contestation.resolution = "resolved", resolution
    await contestation.save()
    return _read(ContestationRead, contestation)


@router.get("/projects/{project_id}/rule-decisions")
async def list_rule_decisions(project_id: str, user: CurrentUser) -> list[RuleDecisionRead]:
    project = await owned_or_404(project_id, user)
    items = await RuleDecision.find(RuleDecision.project_id == str(project.id)).sort(+RuleDecision.created_at).to_list()
    return [_read(RuleDecisionRead, d) for d in items]


@router.post("/projects/{project_id}/rule-decisions", status_code=status.HTTP_201_CREATED)
async def create_rule_decision(project_id: str, body: RuleDecisionIn, user: CurrentUser) -> RuleDecisionRead:
    project = await owned_or_404(project_id, user)
    await _analysis_of(project, body.analysis_id, user)
    item = RuleDecision(**body.model_dump(exclude={"project_id"}, by_alias=False), project_id=str(project.id), author_id=str(user.id))
    await item.insert()
    return _read(RuleDecisionRead, item)


@router.get("/projects/{project_id}/evidence-reviews")
async def list_evidence_reviews(project_id: str, user: CurrentUser) -> list[EvidenceReviewRead]:
    project = await owned_or_404(project_id, user)
    items = await EvidenceReview.find(EvidenceReview.project_id == str(project.id)).sort(+EvidenceReview.created_at).to_list()
    return [_read(EvidenceReviewRead, r) for r in items]


@router.post("/projects/{project_id}/evidence-reviews", status_code=status.HTTP_201_CREATED)
async def create_evidence_review(project_id: str, body: EvidenceReviewIn, user: CurrentUser) -> EvidenceReviewRead:
    project = await owned_or_404(project_id, user)
    await _analysis_of(project, body.analysis_id, user)
    item = EvidenceReview(**body.model_dump(exclude={"project_id"}, by_alias=False), project_id=str(project.id), author_id=str(user.id))
    await item.insert()
    return _read(EvidenceReviewRead, item)
