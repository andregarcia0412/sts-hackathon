"""Benchmark against the real Ollama: PRJ01 (official key) + PRJ21 (preliminary reading). Opt-in: `uv run pytest -m live`."""

from pathlib import Path

import httpx
import pytest

from backend.analyses.jobs import InlineRunner
from backend.analyses.orchestrator import AnalysisService
from backend.benchmark.service import start_benchmark
from backend.catalog.loader import get_catalog
from backend.llm import LLMClient
from backend.search.providers import build_providers
from tests.live.test_live_pipeline import live_settings

pytestmark = pytest.mark.live


async def test_benchmark_prj01_and_prj21(db):
    settings = live_settings()
    root = Path(settings.package_dir)
    sets = {"historico": root / "01_projetos" / "01_historico", "analise": root / "01_projetos" / "02_casos_para_analise"}
    if not all(path.is_dir() for path in sets.values()):
        pytest.skip("PACKAGE_DIR must be the root of the challenge package")
    preliminary = root / "leitura_preliminar.csv"
    async with httpx.AsyncClient(timeout=30) as http:
        llm = LLMClient(settings)
        service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
        benchmark = await start_benchmark("live", "live", sets, service, InlineRunner(),
                                          answer_key=root / "historicos_classificados.csv",
                                          preliminary=preliminary if preliminary.is_file() else None,
                                          projects=["PRJ01", "PRJ21"])
    metrics = benchmark.metrics
    print(metrics.model_dump_json(indent=2))
    assert benchmark.status == "concluido" and len(benchmark.runs) == 2
    assert metrics.accuracy["oficial"].n == 1
    assert metrics.usage.total.calls > 0 and metrics.usage.total.prompt_tokens > 0
    assert metrics.timing.total_s.n == 2
