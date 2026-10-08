"""POST /analyze + GET /status/{id} — fila assíncrona in-process (spec 5/6)."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_microservice.agents.orchestrator import run_analysis
from ai_microservice.config import get_settings

router = APIRouter()

_STEP_ORDER = [
    "ingestao",
    "checagens",
    "interpretação",
    "regras_especiais",
    "especialistas",
    "web_log",
    "grafo",
    "concluida",
]


@dataclass
class AnalysisState:
    analise_id: str
    project_path: str
    project_id: str
    status: str = "pendente"  # pendente | rodando | concluida | falhou
    steps: dict[str, dict] = field(default_factory=dict)
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    result: dict | None = None

    def public(self) -> dict:
        total = None
        if self.started_at and self.finished_at:
            total = round(self.finished_at - self.started_at, 2)
        return {
            "analise_id": self.analise_id,
            "project_id": self.project_id,
            "status": self.status,
            "steps": {
                name: {
                    "status": st.get("status", "pendente"),
                    "inicio": st.get("inicio"),
                    "fim": st.get("fim"),
                    "duracao_s": st.get("duracao_s"),
                }
                for name, st in self.steps.items()
            },
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duracao_total_s": total,
            "error": self.error,
            "version": (self.result or {}).get("version"),
        }


@dataclass
class _Registry:
    analyses: dict[str, AnalysisState] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


_registry = _Registry()


class AnalyzeRequest(BaseModel):
    project_path: str


async def _worker() -> None:
    while True:
        analise_id = await _registry.queue.get()
        state = _registry.analyses[analise_id]
        try:
            state.status = "rodando"
            state.started_at = time.time()
            for name in _STEP_ORDER:
                state.steps[name] = {"status": "pendente"}

            async def status_cb(step: str, st: str):
                now = time.time()
                cur = state.steps.setdefault(step, {"status": st})
                # fecha passo anterior aberto
                for s in state.steps.values():
                    if s.get("status") == "rodando" and s is not cur:
                        s["status"] = "concluida"
                        s["fim"] = now
                        s["duracao_s"] = round(now - s["inicio"], 2)
                cur["status"] = st
                cur["inicio"] = now

            result = await run_analysis(Path(state.project_path), analise_id, status_cb=status_cb)
            state.result = result
            state.status = "concluida"
        except Exception as exc:  # noqa: BLE001 — status é reportado, não propagado
            state.status = "falhou"
            state.error = f"{type(exc).__name__}: {exc}"
        finally:
            state.finished_at = time.time()
            _registry.queue.task_done()


_worker_started = False


def _ensure_worker() -> None:
    global _worker_started
    if not _worker_started:
        asyncio.get_event_loop_policy()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            loop.create_task(_worker())
            _worker_started = True


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    s = get_settings()
    p = Path(req.project_path)
    if not p.is_absolute():
        p = s.data_dir / "casos_test" / p
    if not p.exists():
        raise HTTPException(404, f"projeto não encontrado: {p}")
    analise_id = str(uuid.uuid4())[:8]
    _registry.analyses[analise_id] = AnalysisState(
        analise_id=analise_id,
        project_path=str(p),
        project_id=p.name,
    )
    _ensure_worker()
    await _registry.queue.put(analise_id)
    return {"analise_id": analise_id, "project_id": p.name}


@router.get("/status/{analise_id}")
async def status(analise_id: str):
    state = _registry.analyses.get(analise_id)
    if state is None:
        raise HTTPException(404, f"análise {analise_id} não existe")
    return state.public()