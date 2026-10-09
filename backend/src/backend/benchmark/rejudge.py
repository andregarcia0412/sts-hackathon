"""Re-judge: runs only the conclusion stage (judge → gates → class) over analyses that already finished.

Measuring a change in the judge or the gates with a full benchmark costs ~260k tokens per project; the evidence
is already saved in `Analysis.criteria`, and the judge needs nothing else (~5 calls per analysis). The result is a
new `Benchmark` comparable with its source through `compare`. The source analyses are never written (principle 10):
each one is re-judged on an in-memory copy.
"""

import asyncio
import time
from datetime import UTC, datetime

from beanie import PydanticObjectId

from backend.analyses.models import Analysis, CanonicalRecord
from backend.benchmark.metrics import compute
from backend.benchmark.models import Benchmark, BenchmarkRun, RunSnapshot
from backend.benchmark.service import snapshot_of
from backend.catalog.models import Catalog
from backend.checks.runner import run_checks
from backend.errors import safe_error_message
from backend.graph.judge import JudgeOptions, judge_and_classify
from backend.llm import LLM
from backend.llm.prompts import prompt_hashes
from backend.llm.calls import calls_scope, stage_scope, summarize
from backend.llm.usage import meter_scope


async def create_rejudge(source: Benchmark, owner_id: str, models: dict[str, str | None], catalog: Catalog,
                         options: JudgeOptions, name: str | None = None, projects: list[str] | None = None,
                         repeats: int = 1) -> Benchmark:
    """The new benchmark, still running: one run per finished source analysis and repeat."""
    wanted = {code.upper() for code in projects or []}
    ids = [PydanticObjectId(run.analysis_id) for run in source.runs]
    finished = {str(a.id) for a in await Analysis.find({"_id": {"$in": ids}, "status": "concluida"}).to_list()}
    sources = [run for run in source.runs
               if run.analysis_id in finished and (not wanted or run.code.upper() in wanted)]
    runs = [BenchmarkRun(set=run.set, code=run.code, project_id=run.project_id, analysis_id=run.analysis_id,
                         repeat=(run.repeat - 1) * repeats + repeat)
            for repeat in range(1, repeats + 1) for run in sources]
    benchmark = Benchmark(
        owner_id=owner_id,
        name=name or f"{source.name} · re-julgar",
        expected=source.expected,
        runs=runs,
        config=source.config.model_copy(update={
            "repeats": repeats,
            "projects": sorted(wanted),
            "models": {"judge": models.get("judge")},
            "catalog_version": catalog.versao,
            "prompts": prompt_hashes(),
            "rejudged_from": str(source.id),
            "judge_options": options.model_dump(),
        }),
    )
    if not runs:
        benchmark.errors.append("nenhuma análise concluída no benchmark de origem")
    await benchmark.insert()
    return benchmark


async def _rejudge_one(llm: LLM, catalog: Catalog, options: JudgeOptions, run: BenchmarkRun,
                       analysis: Analysis) -> RunSnapshot:
    started_at, started = datetime.now(UTC), time.monotonic()
    copy = analysis.model_copy(deep=True)
    if copy.checks is None:  # analyses from before the checks stage: zero tokens from the saved canonical
        if record := await CanonicalRecord.find_one(CanonicalRecord.analysis_id == str(analysis.id)):
            copy.checks = run_checks(record.canonical)
    with meter_scope() as usage, calls_scope() as calls, stage_scope("grafo"):
        try:
            outcome = await judge_and_classify(llm, catalog, copy.criteria, options, copy.checks)
        except Exception as error:  # defensive: one analysis failing must not lose the others
            snap = snapshot_of(run, copy)
            snap.status, snap.error = "falhou", f"re-julgar falhou: {safe_error_message(error)}"
            return snap
    copy.scores, copy.criterion_scores = outcome.scores, outcome.criterion_scores
    copy.states, copy.suggestion = outcome.states, outcome.suggestion
    copy.consistency = outcome.consistency
    copy.usage = usage.model_copy(deep=True)
    copy.calls = summarize(calls)
    copy.started_at, copy.finished_at = started_at, datetime.now(UTC)
    copy.total_s = round(time.monotonic() - started, 3)
    snap = snapshot_of(run, copy)
    snap.stages = {"grafo": "concluida"}
    snap.stage_seconds = {"grafo": copy.total_s}
    snap.rejudged = True
    snap.judgements = outcome.states  # the source analysis is never written: this is the only record of them
    return snap


async def run_rejudge(benchmark: Benchmark, llm: LLM, catalog: Catalog, options: JudgeOptions,
                      concurrency: int = 2) -> Benchmark:
    """Judges every run (in parallel, bounded) and closes the benchmark with its metrics."""
    ids = [PydanticObjectId(run.analysis_id) for run in benchmark.runs]
    analyses = {str(a.id): a for a in await Analysis.find({"_id": {"$in": ids}}).to_list()}
    semaphore = asyncio.Semaphore(concurrency)

    async def one(run: BenchmarkRun) -> RunSnapshot:
        async with semaphore:
            snap = await _rejudge_one(llm, catalog, options, run, analyses[run.analysis_id])
            benchmark.snapshots.append(snap)
            await benchmark.save()
            return snap

    await asyncio.gather(*(one(run) for run in benchmark.runs))
    return await close_rejudge(benchmark, catalog)


async def close_rejudge(benchmark: Benchmark, catalog: Catalog) -> Benchmark:
    order = {(run.code, run.repeat): index for index, run in enumerate(benchmark.runs)}
    benchmark.snapshots.sort(key=lambda s: order.get((s.code, s.repeat), 0))
    benchmark.metrics = compute(benchmark.snapshots, benchmark.expected, catalog)
    benchmark.status = "concluido"
    benchmark.finished_at = datetime.now(UTC)
    await benchmark.save()
    return benchmark
