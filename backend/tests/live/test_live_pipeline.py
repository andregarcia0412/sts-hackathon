"""End-to-end against the real Ollama and the real package. Opt-in: `uv run pytest -m live`.

Reads OLLAMA_* and PACKAGE_DIR from backend/.env (the test conftest blanks them for the unit tests).
"""

from pathlib import Path

import httpx
from dotenv import dotenv_values
import pytest

from backend.analyses.orchestrator import AnalysisService
from backend.catalog.loader import get_catalog
from backend.config import BACKEND_ROOT, Settings
from backend.llm import LLMClient
from backend.projects.importer import files_from_directory
from backend.projects.service import create_project
from backend.search.providers import build_providers

pytestmark = pytest.mark.live
LIVE_PROJECT = "PRJ21"


def live_settings() -> Settings:
    env = BACKEND_ROOT / ".env"
    if not env.exists():
        pytest.skip("backend/.env not found")
    values = {key.lower(): value for key, value in dotenv_values(env).items() if value}
    settings = Settings(_env_file=None, **(values | {"mongodb_db": "sts_test"}))
    if not settings.ollama_model or not settings.ollama_api_key or not settings.package_dir:
        pytest.skip("OLLAMA_MODEL, OLLAMA_API_KEY and PACKAGE_DIR must be set in backend/.env")
    return settings


def find_project(root: Path, code: str) -> Path:
    matches = [p for p in root.rglob(code) if p.is_dir()]
    if not matches:
        pytest.skip(f"{code} not found under PACKAGE_DIR")
    return matches[0]


async def test_prj21_end_to_end(db):
    settings = live_settings()
    folder = find_project(Path(settings.package_dir), LIVE_PROJECT)
    project = await create_project("live", LIVE_PROJECT, files_from_directory(folder))
    async with httpx.AsyncClient(timeout=30) as http:
        llm = LLMClient(settings)
        service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
        analysis = await service.run(str((await service.create(project)).id))

    print({s.name: (s.status, s.duration_s, s.error) for s in analysis.stages})
    print("classe sugerida:", analysis.suggestion and analysis.suggestion.suggested_class)
    print({c: s.state for c, s in analysis.states.items()})
    assert analysis.status == "concluida"
    assert analysis.stage("extracao").status == "concluida"
    evidences = [e for r in analysis.criteria.values() for run in r.rules for e in run.evidences]
    assert evidences, "the real model produced no gated evidence"
    assert all(e.quote for e in evidences)
    assert analysis.report
