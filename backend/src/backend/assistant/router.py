from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status

from backend.analyses.deps import owned_analysis
from backend.api_schema import CamelModel
from backend.assistant.answer import Assistant, AssistantAnswer
from backend.auth.dependencies import CurrentUser
from backend.catalog.loader import get_catalog
from backend.errors import safe_error_message
from backend.frontend_api.projection import project_analysis
from backend.projects.models import Project
from backend.review.models import Contestation

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantContext(CamelModel):
    screen: Literal["analysis", "decision"] = "analysis"
    analysis: dict[str, Any] | None = None  # the front-end sends the tree; only its id is used (data comes from the DB)
    selected_node_id: str | None = None
    debate_node_id: str | None = None


class AskRequest(CamelModel):
    question: str
    context: AssistantContext = AssistantContext()


class DebateRequest(CamelModel):
    node_id: str
    context: AssistantContext = AssistantContext()


async def _tree(context: AssistantContext, user):
    analysis_id = (context.analysis or {}).get("id")
    if not analysis_id:
        return None, None
    analysis = await owned_analysis(analysis_id, str(user.id))
    project = await Project.get(analysis.project_id)
    contestations = await Contestation.find(Contestation.analysis_id == str(analysis.id)).to_list()
    return analysis, project_analysis(get_catalog(), analysis, project, contestations)


def _assistant(request: Request) -> Assistant:
    return Assistant(request.app.state.llm, get_catalog(), request.app.state.norm_index)


@router.post("/ask")
async def ask(body: AskRequest, request: Request, user: CurrentUser) -> AssistantAnswer:
    analysis, tree = await _tree(body.context, user)
    try:
        return await _assistant(request).ask(body.question, analysis, tree, body.context.selected_node_id,
                                             body.context.debate_node_id)
    except Exception as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"assistente indisponível: {safe_error_message(error)}")


@router.post("/debate")
async def debate(body: DebateRequest, request: Request, user: CurrentUser) -> AssistantAnswer:
    _, tree = await _tree(body.context, user)
    if tree is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "context.analysis.id is required")
    return _assistant(request).debate_opening(body.node_id, tree)
