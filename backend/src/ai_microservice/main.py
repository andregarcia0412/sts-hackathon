"""FastAPI: rotas + montagem de /viz (página de teste estática) + CORS do frontend."""
from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai_microservice.api.analyze import router as analyze_router
from ai_microservice.api.graph import router as graph_router
from ai_microservice.api.projects import router as projects_router

# Origens de dev do frontend (Vite 5173); sem credenciais (api é pública em dev)
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(title="STS 2026 — Pipeline de Agentes de Evidências")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(analyze_router)
app.include_router(graph_router)
app.include_router(projects_router)

_STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/viz")
def viz():
    return FileResponse(_STATIC / "viz" / "index.html")


@app.get("/")
def read_root():
    return {"status": "ok", "docs": "/docs", "viz": "/viz"}


def main() -> None:
    uvicorn.run("ai_microservice.main:app", host="127.0.0.1", port=8000, reload=False)