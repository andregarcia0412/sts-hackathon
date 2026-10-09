import csv
import io

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.analyses.deps import Runner, Service, inside_package_dir
from backend.auth.dependencies import CurrentUser
from backend.benchmark.metrics import compare_metrics
from backend.benchmark.models import Benchmark
from backend.benchmark.schemas import (
    BenchmarkComparison,
    BenchmarkProjectRow,
    BenchmarkRead,
    BenchmarkRequest,
    BenchmarkSummary,
    RejudgeRequest,
)
from backend.benchmark.rejudge import create_rejudge, run_rejudge
from backend.benchmark.service import analyses_of, progress, refresh, start_benchmark
from backend.config import settings
from backend.graph.judge import JudgeOptions

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# Layout of the challenge package (PACKAGE_DIR = its root folder).
DEFAULT_DIRS = {"historico": "01_projetos/01_historico", "analise": "01_projetos/02_casos_para_analise"}
DEFAULT_ANSWER_KEY = "historicos_classificados.csv"
DEFAULT_PRELIMINARY = "leitura_preliminar.csv"


def _optional_file(path: str | None, default: str):
    if path:
        return inside_package_dir(path, file=True)
    candidate = settings.package_dir / default if settings.package_dir else None
    return candidate if candidate and candidate.is_file() else None


async def _owned(benchmark_id: str, user, request: Request) -> Benchmark:
    try:
        benchmark = await Benchmark.get(PydanticObjectId(benchmark_id))
    except (InvalidId, TypeError):
        benchmark = None
    if benchmark is None or benchmark.owner_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Benchmark not found")
    return await refresh(benchmark, request.app.state.analysis_service.catalog)


async def _summary(benchmark: Benchmark) -> BenchmarkSummary:
    return BenchmarkSummary.of(benchmark, progress(benchmark, await analyses_of(benchmark)))


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_benchmark(body: BenchmarkRequest, user: CurrentUser, service: Service, runner: Runner) -> BenchmarkRead:
    """Runs the real pipeline over the package sets in the background; poll GET /benchmarks/{id}."""
    overrides = {"historico": body.historico_dir, "analise": body.analise_dir}
    sets = {s: inside_package_dir(overrides[s] or DEFAULT_DIRS[s]) for s in dict.fromkeys(body.sets)}
    answer_key = _optional_file(body.answer_key, DEFAULT_ANSWER_KEY)
    preliminary = _optional_file(body.preliminary_key, DEFAULT_PRELIMINARY)
    benchmark = await start_benchmark(str(user.id), body.name or "benchmark", sets, service, runner,
                                      answer_key=answer_key, preliminary=preliminary, repeats=body.repeats,
                                      projects=body.projects)
    if not benchmark.runs:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "; ".join(benchmark.errors) or "No project found")
    return BenchmarkRead.of(benchmark, progress(benchmark, await analyses_of(benchmark)))


@router.get("")
async def list_benchmarks(user: CurrentUser, request: Request) -> list[BenchmarkSummary]:
    catalog = request.app.state.analysis_service.catalog
    benchmarks = await Benchmark.find(Benchmark.owner_id == str(user.id)).sort(-Benchmark.created_at).to_list()
    return [await _summary(await refresh(b, catalog)) for b in benchmarks]


@router.get("/compare")
async def compare(base: str, target: str, user: CurrentUser, request: Request) -> BenchmarkComparison:
    """Deltas of the headline metrics between two finished benchmarks, plus what changed in the config."""
    old, new = await _owned(base, user, request), await _owned(target, user, request)
    if old.metrics is None or new.metrics is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Both benchmarks must have finished")
    roles = sorted(set(old.config.models) | set(new.config.models))
    prompts = sorted(set(old.config.prompts) | set(new.config.prompts))
    return BenchmarkComparison(
        base=await _summary(old), target=await _summary(new), deltas=compare_metrics(old.metrics, new.metrics),
        models_changed={r: {"base": old.config.models.get(r), "target": new.config.models.get(r)}
                        for r in roles if old.config.models.get(r) != new.config.models.get(r)},
        prompts_changed=[p for p in prompts if old.config.prompts.get(p) != new.config.prompts.get(p)],
        catalog_changed=old.config.catalog_version != new.config.catalog_version,
    )


@router.post("/{benchmark_id}/rejudge", status_code=status.HTTP_202_ACCEPTED)
async def rejudge_benchmark(benchmark_id: str, body: RejudgeRequest, user: CurrentUser, request: Request,
                            service: Service, runner: Runner) -> BenchmarkRead:
    """Re-runs only the judge → gates → class over the finished analyses of a benchmark (~5 calls each).

    The source analyses are never written; the result is a new benchmark, comparable through /compare."""
    source = await _owned(benchmark_id, user, request)
    options = JudgeOptions.from_settings(service.settings, coherence_mode=body.coherence)
    benchmark = await create_rejudge(source, str(user.id), service.models_by_role(), service.catalog, options,
                                     name=body.name, projects=body.projects, repeats=body.repeats)
    if not benchmark.runs:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "; ".join(benchmark.errors))
    # One job slot of the runner = one analysis at a time, like any other background job.
    await runner.submit(lambda: run_rejudge(benchmark, service.llm, service.catalog, options, concurrency=1))
    benchmark = await Benchmark.get(benchmark.id)
    return BenchmarkRead.of(benchmark, progress(benchmark, {}))


@router.get("/{benchmark_id}")
async def get_benchmark(benchmark_id: str, user: CurrentUser, request: Request) -> BenchmarkRead:
    benchmark = await _owned(benchmark_id, user, request)
    return BenchmarkRead.of(benchmark, progress(benchmark, await analyses_of(benchmark)))


def _rows(benchmark: Benchmark) -> list[BenchmarkProjectRow]:
    return [BenchmarkProjectRow.of(snap, benchmark.expected.get(snap.code))
            for snap in sorted(benchmark.snapshots, key=lambda s: (s.set, s.code, s.repeat))]


@router.get("/{benchmark_id}/projects")
async def benchmark_projects(benchmark_id: str, user: CurrentUser, request: Request) -> list[BenchmarkProjectRow]:
    """One line per analysed project: expected × suggested, time, tokens, evidence, divergences."""
    benchmark = await _owned(benchmark_id, user, request)
    if benchmark.status != "concluido":
        raise HTTPException(status.HTTP_409_CONFLICT, "Benchmark still running")
    return _rows(benchmark)


@router.get("/{benchmark_id}/report.csv")
async def benchmark_csv(benchmark_id: str, user: CurrentUser, request: Request) -> Response:
    benchmark = await _owned(benchmark_id, user, request)
    if benchmark.status != "concluido":
        raise HTTPException(status.HTTP_409_CONFLICT, "Benchmark still running")
    rows = [row.csv_row() for row in _rows(benchmark)]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]) if rows else ["projeto_id"], delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return Response("﻿" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="benchmark_{benchmark.id}.csv"'})
