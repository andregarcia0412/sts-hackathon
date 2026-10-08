import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.analyses.jobs import JobRunner
from backend.analyses.orchestrator import AnalysisService
from backend.analyses.router import router as analyses_router
from backend.assistant.norms import ingest_norms, load_norm_index, norm_index
from backend.assistant.router import router as assistant_router
from backend.auth.router import router as auth_router
from backend.benchmark.router import router as benchmark_router
from backend.catalog.loader import get_catalog, sync_catalog_to_db
from backend.catalog.router import router as catalog_router
from backend.config import settings
from backend.projects.router import router as projects_router
from backend.database import close_db, init_db, ping_db
from backend.llm import LLMClient
from backend.search.providers import build_providers
from backend.report.router import router as report_router
from backend.review.router import router as review_router
from backend.users.router import router as users_router
from backend.users.seed import seed_users

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_users()
    await sync_catalog_to_db(get_catalog())
    await AnalysisService.mark_interrupted()
    http = httpx.AsyncClient(timeout=30)
    llm = LLMClient(settings)
    app.state.llm = llm
    app.state.runner = JobRunner(settings.analysis_concurrency)
    app.state.analysis_service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
    app.state.norm_index = await load_norm_index()
    ingestion = None
    if not app.state.norm_index.chunks and settings.norms_auto_ingest and any(settings.norms_dir.glob("*.pdf")):
        ingestion = asyncio.create_task(_ingest_norms(app))
    yield
    if ingestion and not ingestion.done():
        ingestion.cancel()
    await http.aclose()
    await close_db()


async def _ingest_norms(app: FastAPI) -> None:
    """First start: index the normative PDFs in the background (the chatbot answers from graph meanwhile)."""
    try:
        app.state.norm_index = norm_index(await ingest_norms(settings.norms_dir))
        logging.getLogger(__name__).info("normative base indexed: %d chunks", len(app.state.norm_index.chunks))
    except Exception:
        logging.getLogger(__name__).exception("normative base ingestion failed")


app = FastAPI(title="STS 2026 — Lei do Bem", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(projects_router)
app.include_router(analyses_router)
app.include_router(review_router)
app.include_router(report_router)
app.include_router(assistant_router)
app.include_router(benchmark_router)


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health/db")
async def db_health():
    return {"mongo": "ok" if await ping_db() else "unreachable"}


def main() -> None:
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
