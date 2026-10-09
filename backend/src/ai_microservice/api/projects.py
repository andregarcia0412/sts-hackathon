"""GET /ai-projects — projetos com grafo salvo no pipeline (para o frontend).

Lista `data/graphs/*` com a versão mais recente (o primeiro item de _versions
mais alto). Sem auth (dev/hackathon); leitura barata em disco.
"""
from __future__ import annotations

from fastapi import APIRouter

from ai_microservice.config import get_settings
from ai_microservice.graph.store import JSONFileGraphStore

router = APIRouter()


@router.get("/ai-projects")
async def list_ai_projects():
    s = get_settings()
    store = JSONFileGraphStore(base_dir=s.graphs_dir)
    base = store.base_dir
    projects: list[dict] = []
    if base.exists():
        for project_dir in sorted(base.iterdir()):
            if not project_dir.is_dir():
                continue
            versions = sorted(
                (d.name for d in project_dir.iterdir() if d.is_dir() and d.name.startswith("v")),
                key=lambda n: int(n[1:]),
            )
            if not versions:
                continue
            latest = versions[-1]
            meta: dict = {}
            meta_path = project_dir / latest / "meta.json"
            if meta_path.exists():
                import json

                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    meta = {}
            projects.append(
                {
                    "project_id": project_dir.name,
                    "version": latest,
                    "generated_at": meta.get("timestamp"),
                    "nodes": meta.get("nodes"),
                    "edges": meta.get("edges"),
                }
            )
    return {"projects": projects}