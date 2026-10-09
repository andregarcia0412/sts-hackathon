"""Processing the cases for the delivery (spec 08): a benchmark of the `analise` set, with an estimate before it
starts and `--resume` to redo only what failed or changed (each full round of 20 costs ~5M tokens)."""

import hashlib
import math
from pathlib import Path

from beanie import PydanticObjectId

from backend.analyses.batch import groups_from_directory
from backend.analyses.models import Analysis
from backend.benchmark.models import Benchmark
from backend.benchmark.service import start_benchmark
from backend.delivery.export import latest_analyses
from backend.llm.prompts import prompt_hashes
from backend.projects.importer import project_code_from


def estimate(n_projects: int, concurrency: int, last: Benchmark | None) -> str:
    if last is None or last.metrics is None or last.metrics.usage.tokens_per_run.median is None:
        return f"{n_projects} projetos (sem benchmark anterior para estimar tokens e tempo)"
    tokens = last.metrics.usage.tokens_per_run.median * n_projects
    minutes = math.ceil(n_projects / max(concurrency, 1)) * (last.metrics.timing.total_s.median or 0) / 60
    return (f"{n_projects} projetos × ~{last.metrics.usage.tokens_per_run.median / 1000:.0f} mil tokens ≈ "
            f"{tokens / 1e6:.1f} milhões de tokens, ~{minutes:.0f} min com ANALYSIS_CONCURRENCY={concurrency} "
            f"(medianas do benchmark {last.id})")


def _file_hashes(folder: Path) -> dict[str, str]:
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def unchanged(analysis: Analysis, folder: Path, catalog_version: str) -> bool:
    """Same files, catalog and prompts: the finished analysis can be delivered as it is."""
    if analysis.versions.catalog_version != catalog_version:
        return False
    if analysis.versions.prompts and analysis.versions.prompts != prompt_hashes():
        return False
    return analysis.versions.file_hashes == _file_hashes(folder)


async def pending_codes(folder: Path, resume: Benchmark | None, catalog_version: str,
                        projects: list[str] | None = None) -> tuple[list[str], list[str]]:
    """(codes to analyse, codes reused from the resumed benchmark)."""
    wanted = {c.upper() for c in projects or []}
    folders = {(project_code_from(name) or name).upper(): folder / name for name, _ in groups_from_directory(folder)}
    codes = sorted(c for c in folders if not wanted or c in wanted)
    if resume is None:
        return codes, []
    analyses, _ = await latest_analyses(resume)
    reused = [c for c in codes if c in analyses and unchanged(analyses[c], folders[c], catalog_version)]
    return [c for c in codes if c not in reused], reused


async def run_delivery(owner_id: str, name: str, folder: Path, service, runner, preliminary: Path | None,
                       projects: list[str] | None = None, resume: Benchmark | None = None) -> Benchmark:
    todo, reused = await pending_codes(folder, resume, service.catalog.versao, projects)
    if not todo and resume is not None:
        return resume
    benchmark = await start_benchmark(owner_id, name, {"analise": folder}, service, runner, preliminary=preliminary,
                                      projects=todo)
    if resume is not None:
        benchmark.config.resumed_from = str(resume.id)
        benchmark.errors.append(f"retomado de {resume.id}: {len(reused)} projeto(s) reaproveitado(s)")
        await benchmark.save()
    return benchmark


async def last_finished_benchmark(owner_id: str) -> Benchmark | None:
    return await Benchmark.find(Benchmark.owner_id == owner_id, Benchmark.status == "concluido",
                                {"config.rejudgedFrom": None}).sort(-Benchmark.created_at).first_or_none()


async def get_benchmark(benchmark_id: str) -> Benchmark | None:
    return await Benchmark.get(PydanticObjectId(benchmark_id))
