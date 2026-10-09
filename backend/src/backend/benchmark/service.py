"""Benchmark: runs the real pipeline over the package sets, then measures it against the expected cases.

There is no coordinator task: the analyses run in the normal queue and `refresh` closes the benchmark
(snapshots + metrics) the first time it sees every analysis finished. A server restart fails the
running analyses (`mark_interrupted`), so the benchmark still closes, counting them as failures.
"""

import hashlib
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from beanie import PydanticObjectId

from backend.analyses.batch import groups_from_directory, import_projects
from backend.analyses.deps import start_analysis
from backend.analyses.models import Analysis
from backend.analyses.orchestrator import AnalysisService
from backend.benchmark.metrics import compute
from backend.benchmark.models import (
    Benchmark,
    BenchmarkConfig,
    BenchmarkRun,
    DivergenceSnapshot,
    PackageSet,
    RunSnapshot,
)
from backend.benchmark.reference import ExpectedCase, load_answer_key, load_preliminary
from backend.catalog.models import Catalog
from backend.llm.prompts import prompt_hashes
from backend.projects.importer import project_code_from
from backend.projects.models import Project

FINISHED = ("concluida", "falhou")
RULES_RUN = ("executada", "sem_evidencia", "nao_executada")  # N/A and partial rules leave without the LLM


def _sha256(path: Path | None) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path else None


def _backend_version() -> str | None:
    try:
        return version("backend")
    except PackageNotFoundError:
        return None


def search_config(settings) -> dict[str, int]:
    return {"web_queries_per_front": settings.web_queries_per_front,
            "web_results_per_query": settings.web_results_per_query,
            "web_fetch_per_front": settings.web_fetch_per_front,
            "analysis_concurrency": settings.analysis_concurrency,
            "openalex_max_concurrency": settings.openalex_max_concurrency}


def load_expected(catalog: Catalog, answer_key: Path | None, preliminary: Path | None) -> dict[str, ExpectedCase]:
    expected = load_preliminary(preliminary) if preliminary else {}
    if answer_key:
        expected |= load_answer_key(answer_key, catalog)  # the official key always wins
    return expected


async def start_benchmark(owner_id: str, name: str, sets: dict[PackageSet, Path], service: AnalysisService, runner,
                          answer_key: Path | None = None, preliminary: Path | None = None, repeats: int = 1,
                          projects: list[str] | None = None) -> Benchmark:
    wanted = {code.upper() for code in projects or []}
    benchmark = Benchmark(
        owner_id=owner_id,
        name=name,
        expected=load_expected(service.catalog, answer_key, preliminary),
        config=BenchmarkConfig(
            sets={s: str(path) for s, path in sets.items()},
            answer_key=str(answer_key) if answer_key else None,
            answer_key_sha256=_sha256(answer_key),
            preliminary_key=str(preliminary) if preliminary else None,
            preliminary_key_sha256=_sha256(preliminary),
            repeats=repeats,
            projects=sorted(wanted),
            models=service.models_by_role(),
            catalog_version=service.catalog.versao,
            prompts=prompt_hashes(),
            backend_version=_backend_version(),
            search=search_config(service.settings),
        ),
    )
    await benchmark.insert()
    benchmark_id = str(benchmark.id)
    for package_set, folder in sets.items():
        groups = [(name_, files) for name_, files in groups_from_directory(folder)
                  if not wanted or (project_code_from(name_) or "").upper() in wanted]
        if not groups:
            benchmark.errors.append(f"{package_set}: nenhum projeto encontrado em {folder}")
            continue
        batch = await import_projects(groups, owner_id, f"{name} · {package_set}", service, runner,
                                      benchmark_id=benchmark_id)
        benchmark.batch_ids.append(str(batch.id))
        for project_id, analysis_id in zip(batch.project_ids, batch.analysis_ids, strict=True):
            project = await Project.get(PydanticObjectId(project_id))
            benchmark.runs.append(BenchmarkRun(set=package_set, code=project.code or project.name,
                                               project_id=project_id, analysis_id=analysis_id, repeat=1))
        await benchmark.save()
        for repeat in range(2, repeats + 1):  # a repeat is a new version of the same project's analysis
            for project_id in batch.project_ids:
                project = await Project.get(PydanticObjectId(project_id))
                analysis = await start_analysis(project, service, runner, batch_id=str(batch.id))
                benchmark.runs.append(BenchmarkRun(set=package_set, code=project.code or project.name,
                                                   project_id=project_id, analysis_id=str(analysis.id), repeat=repeat))
            await benchmark.save()
    await benchmark.save()
    return await refresh(benchmark, service.catalog)


async def analyses_of(benchmark: Benchmark) -> dict[str, Analysis]:
    ids = [PydanticObjectId(run.analysis_id) for run in benchmark.runs]
    return {str(a.id): a for a in await Analysis.find({"_id": {"$in": ids}}).to_list()}


def progress(benchmark: Benchmark, analyses: dict[str, Analysis]) -> dict[str, int]:
    counts = dict.fromkeys(("pendente", "rodando", "concluida", "falhou"), 0)
    if benchmark.config.rejudged_from:  # its runs point at the source analyses, which finished long ago
        for snap in benchmark.snapshots:
            counts["falhou" if snap.status == "falhou" else "concluida"] += 1
        counts["pendente"] = len(benchmark.runs) - len(benchmark.snapshots)
        return counts
    for run in benchmark.runs:
        status = analyses[run.analysis_id].status if run.analysis_id in analyses else "falhou"
        counts[status] = counts.get(status, 0) + 1
    return counts


def snapshot_of(run: BenchmarkRun, analysis: Analysis | None) -> RunSnapshot:
    if analysis is None:
        return RunSnapshot(set=run.set, code=run.code, repeat=run.repeat, analysis_id=run.analysis_id,
                           status="falhou", error="análise não encontrada")
    snap = RunSnapshot(
        set=run.set, code=run.code, repeat=run.repeat, analysis_id=run.analysis_id,
        status=analysis.status, error=analysis.error,
        started_at=analysis.started_at, finished_at=analysis.finished_at, total_s=analysis.total_s,
        stages={s.name: s.status for s in analysis.stages},
        stage_seconds={s.name: s.duration_s for s in analysis.stages if s.duration_s is not None},
        states={c: s.state for c, s in analysis.states.items()},
        columns={c: s.column for c, s in analysis.states.items()},
        criterion_scores=dict(analysis.criterion_scores),
        usage=analysis.usage,
        coherence={c: s.coherence for c, s in analysis.states.items() if s.coherence},
        neutralized=len(analysis.consistency.neutralized) if analysis.consistency else 0,
        files_total=sum(analysis.mapping_sources.values()),
        files_by_agent=analysis.mapping_sources.get("agente", 0),
    )
    if suggestion := analysis.suggestion:
        snap.suggested_class, snap.inconsistent = suggestion.suggested_class, suggestion.inconsistent
        snap.incomplete = bool(suggestion.incomplete)
    for result in analysis.criteria.values():
        for rule in result.rules:
            if rule.status in RULES_RUN:
                snap.rules_total += 1
                snap.rules_with_evidence += bool(rule.evidences)
                snap.rules_not_executed += rule.status == "nao_executada"
            snap.gate_dropped += len(rule.dropped)
            for item in rule.evidences:
                snap.evidence_ids.append(item.id)
                snap.evidences_positive += item.polarity == "positiva"
                snap.evidences_negative += item.polarity == "negativa"
        snap.web_searches += len(result.search_log)
        snap.web_search_errors += sum(1 for entry in result.search_log if entry.error)
        snap.web_searches_reused += sum(1 for entry in result.search_log if entry.reused_from)
        snap.web_queries_ungrounded += sum(1 for entry in result.search_log
                                           if entry.error and "sem termo do domínio" in entry.error)
        for entry in result.search_log:
            snap.web_searches_by_base[entry.base] = snap.web_searches_by_base.get(entry.base, 0) + 1
            if entry.error:
                snap.web_search_errors_by_base[entry.base] = snap.web_search_errors_by_base.get(entry.base, 0) + 1
        snap.sanitized_terms_removed += sum(len(entry.removed_terms) for entry in result.search_log)
        snap.web_sources += len(result.web_sources)
        snap.web_not_prior_art += sum(1 for source in result.web_sources if source.prior_art is False)
        snap.divergences += [DivergenceSnapshot(criterion=d.criterion, testimony_quote=d.testimony_quote,
                                                record_quote=d.record_quote, statement=d.statement)
                             for d in result.divergences]
        snap.missing_links += len(result.missing_links)
    return snap


UNFINISHED = "não terminou: benchmark fechado antes do fim da análise"


async def close(benchmark: Benchmark, catalog: Catalog) -> Benchmark:
    """Closes a benchmark now (a CLI that died mid-run): what finished counts, the rest counts as failure."""
    if benchmark.status == "concluido":
        return benchmark
    if benchmark.config.rejudged_from:
        done = {(s.code, s.repeat) for s in benchmark.snapshots}
        benchmark.snapshots += [RunSnapshot(set=run.set, code=run.code, repeat=run.repeat, analysis_id=run.analysis_id,
                                            status="falhou", error=UNFINISHED, rejudged=True)
                                for run in benchmark.runs if (run.code, run.repeat) not in done]
    else:
        analyses = await analyses_of(benchmark)
        benchmark.snapshots = [snapshot_of(run, analyses.get(run.analysis_id)) for run in benchmark.runs]
        for snap in benchmark.snapshots:
            if snap.status not in FINISHED:
                snap.status, snap.error = "falhou", UNFINISHED
    benchmark.metrics = compute(benchmark.snapshots, benchmark.expected, catalog)
    benchmark.status = "concluido"
    benchmark.finished_at = datetime.now(UTC)
    benchmark.errors.append("fechado à força")
    await benchmark.save()
    return benchmark


async def refresh(benchmark: Benchmark, catalog: Catalog, force: bool = False) -> Benchmark:
    """Closes the benchmark once every analysis has finished (idempotent; a no-op while running or closed).
    `force` closes it now, counting the unfinished analyses as failures."""
    if force:
        return await close(benchmark, catalog)
    if benchmark.status == "concluido" or benchmark.config.rejudged_from:  # a re-judge closes itself
        return benchmark
    analyses = await analyses_of(benchmark)
    if any(analyses[run.analysis_id].status not in FINISHED for run in benchmark.runs if run.analysis_id in analyses):
        return benchmark
    benchmark.snapshots = [snapshot_of(run, analyses.get(run.analysis_id)) for run in benchmark.runs]
    benchmark.metrics = compute(benchmark.snapshots, benchmark.expected, catalog)
    benchmark.status = "concluido"
    benchmark.finished_at = datetime.now(UTC)
    await benchmark.save()
    return benchmark
