from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from ai_microservice.config import get_settings
from ai_microservice.documents.pdf import DocumentError, extract_text
from ai_microservice.jobs import Job, JobStore, get_job_store
from ai_microservice.llm import get_llm_client
from ai_microservice.modules.novelty.orchestrator import JOB_KIND, STEPS, NoveltyPipeline
from ai_microservice.modules.novelty.schemas import JobCreated

router = APIRouter(prefix="/novelty", tags=["novidade"])


def get_pipeline(store: Annotated[JobStore, Depends(get_job_store)]) -> NoveltyPipeline:
    return NoveltyPipeline(get_llm_client(), get_settings(), store)


async def _read_pdf(upload: UploadFile, field: str) -> str:
    try:
        return extract_text(await upload.read())
    except DocumentError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field}: {error}") from error


@router.post("/analyses", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreated)
async def create_analysis(
    background: BackgroundTasks,
    store: Annotated[JobStore, Depends(get_job_store)],
    pipeline: Annotated[NoveltyPipeline, Depends(get_pipeline)],
    dossie: Annotated[UploadFile, File(description="Dossiê do projeto (PDF)")],
    entrevista: Annotated[UploadFile | None, File(description="Transcrição da entrevista técnica (PDF)")] = None,
    data_inicio: Annotated[date | None, Form(description="Data de início do projeto, se não der para calcular pelo dossiê")] = None,
) -> JobCreated:
    dossie_text = await _read_pdf(dossie, "dossie")
    entrevista_text = await _read_pdf(entrevista, "entrevista") if entrevista else None
    job = store.create(JOB_KIND, STEPS)
    background.add_task(pipeline.run, job.job_id, dossie_text, entrevista_text, data_inicio)
    return JobCreated(job_id=job.job_id)


@router.get("/analyses/{job_id}", response_model=Job)
def get_analysis(job_id: str, store: Annotated[JobStore, Depends(get_job_store)]) -> Job:
    job = store.get(job_id)
    if job is None or job.kind != JOB_KIND:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Análise não encontrada")
    return job
