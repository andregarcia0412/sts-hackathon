from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel

from backend.analyses.deps import owned_analysis
from backend.analyses.models import Analysis, Batch
from backend.auth.dependencies import CurrentUser
from backend.catalog.loader import get_catalog
from backend.report.builder import AnalystDecisionInfo, Parecer, build_parecer
from backend.report.export import answer_key_row, to_csv
from backend.report.pdf import render_pdf
from backend.review.models import Decision

router = APIRouter(tags=["report"])


async def _parecer(analysis: Analysis) -> Parecer:
    if analysis.status != "concluida" or not analysis.report:
        raise HTTPException(status.HTTP_409_CONFLICT, "Report not available: the analysis has not finished")
    decisions = await Decision.find(Decision.project_id == analysis.project_id).sort(+Decision.decided_at).to_list()
    infos = [AnalystDecisionInfo(outcome=d.outcome, justification=d.justification, analyst_name=d.analyst_name,
                                 decided_at=d.decided_at) for d in decisions]
    return build_parecer(get_catalog(), analysis, infos)


def _camel(value):
    if isinstance(value, dict):
        return {to_camel(k): _camel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_camel(v) for v in value]
    return value


def _filename(parecer: Parecer, extension: str) -> dict[str, str]:
    name = f"parecer_{parecer.projeto_id or 'projeto'}_v{parecer.rastreabilidade.version}.{extension}"
    return {"Content-Disposition": f'attachment; filename="{name}"'}


@router.get("/analyses/{analysis_id}/report.json")
async def report_json(analysis_id: str, user: CurrentUser) -> JSONResponse:
    parecer = await _parecer(await owned_analysis(analysis_id, str(user.id)))
    return JSONResponse(_camel(parecer.model_dump(mode="json")))


@router.get("/analyses/{analysis_id}/report.csv")
async def report_csv(analysis_id: str, user: CurrentUser) -> Response:
    parecer = await _parecer(await owned_analysis(analysis_id, str(user.id)))
    return Response(to_csv([answer_key_row(parecer)]), media_type="text/csv; charset=utf-8", headers=_filename(parecer, "csv"))


@router.get("/analyses/{analysis_id}/report.pdf")
async def report_pdf(analysis_id: str, user: CurrentUser) -> Response:
    parecer = await _parecer(await owned_analysis(analysis_id, str(user.id)))
    return Response(render_pdf(parecer), media_type="application/pdf", headers=_filename(parecer, "pdf"))


@router.get("/batches/{batch_id}/report.csv")
async def batch_report_csv(batch_id: str, user: CurrentUser) -> Response:
    try:
        batch = await Batch.get(PydanticObjectId(batch_id))
    except (InvalidId, TypeError):
        batch = None
    if batch is None or batch.owner_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Batch not found")
    analyses = await Analysis.find({"batch_id": str(batch.id), "status": "concluida"}).to_list()
    rows = [answer_key_row(await _parecer(a)) for a in analyses if a.report]
    rows.sort(key=lambda row: row["projeto_id"])
    return Response(to_csv(rows), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="lote_{batch.name}.csv"'})
