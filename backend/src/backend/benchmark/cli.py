"""`uv run backend-benchmark`: runs the pipeline over the package and prints accuracy, time and cost."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx
from beanie import PydanticObjectId

from backend.analyses.jobs import JobRunner
from backend.analyses.orchestrator import AnalysisService
from backend.benchmark.metrics import headline
from backend.benchmark.models import Benchmark, BenchmarkMetrics
from backend.benchmark.rejudge import create_rejudge, run_rejudge
from backend.benchmark.router import DEFAULT_ANSWER_KEY, DEFAULT_DIRS, DEFAULT_PRELIMINARY
from backend.benchmark.schemas import BenchmarkRead
from backend.benchmark.service import analyses_of, progress, refresh, start_benchmark
from backend.catalog.loader import get_catalog, sync_catalog_to_db
from backend.config import settings
from backend.database import close_db, init_db
from backend.graph.judge import JudgeOptions
from backend.llm import LLMClient
from backend.search.providers import build_providers
from backend.users.seed import seed_users
from backend.users.service import get_user_by_email


def _default(path: Path | None, relative: str, file: bool = False) -> Path | None:
    if path is not None:
        return path.resolve()
    candidate = settings.package_dir / relative if settings.package_dir else None
    if candidate and (candidate.is_file() if file else candidate.is_dir()):
        return candidate
    return None


def print_summary(metrics: BenchmarkMetrics) -> None:
    for reference, acc in metrics.accuracy.items():
        tag = "gabarito oficial" if reference == "oficial" else "leitura preliminar (NÃO oficial)"
        print(f"\n== Acurácia · {tag}: {acc.class_hits}/{acc.n} = {acc.class_accuracy} · macro-F1 {acc.macro_f1} "
              f"· kappa {acc.cohen_kappa} · falsos elegíveis {acc.false_eligible}")
        if acc.state_accuracy:
            print("   estados:", ", ".join(f"{c} {v}" for c, v in acc.state_accuracy.items()))
        if acc.planted_divergences:
            print(f"   divergências plantadas achadas: {acc.planted_divergences_found}/{acc.planted_divergences}")
        for miss in acc.misses:
            print(f"   ✗ {miss}")
    t, u, r = metrics.timing, metrics.usage, metrics.reliability
    print(f"\n== Tempo: mediana {t.total_s.median} s · p95 {t.total_s.p95} s · máx {t.total_s.max} s · "
          f"wall-clock {t.wall_clock_s} s · {t.projects_per_hour} projetos/h")
    for stage, d in t.stages_s.items():
        print(f"   {stage:9} mediana {d.median} s · p95 {d.p95} s")
    print(f"== LLM: {u.total.calls} chamadas · {u.total.prompt_tokens + u.total.completion_tokens} tokens "
          f"(média {u.tokens_per_run.mean}/projeto) · retries {u.total.transport_retries} transporte, "
          f"{u.total.schema_retries} schema · {u.web_search_calls} buscas web")
    print(f"== Confiabilidade: falhas {r.failed}/{r.runs} · inconsistentes {r.inconsistent_rate} · "
          f"sem classe {r.no_class_rate} · regras não executadas {r.rules_not_executed_rate}")
    e = metrics.evidence
    print(f"== Evidência: cobertura de regras {e.rule_coverage} · descarte no gate {e.gate_drop_rate} · "
          f"divergências/projeto {e.divergences_per_run.mean}")
    if d := metrics.determinism:
        print(f"== Determinismo: classe {d.class_agreement} · jaccard evidências {d.evidence_jaccard} · "
              f"instáveis: {', '.join(d.unstable) or '-'}")


async def run(args: argparse.Namespace, service: AnalysisService, runner) -> Benchmark:
    owner = await get_user_by_email(args.owner)
    if owner is None:
        raise SystemExit(f"user not found: {args.owner}")
    folders = {"historico": args.historico, "analise": args.analise}
    sets = {s: _default(folders[s], DEFAULT_DIRS[s]) for s in args.sets}
    if missing := [s for s, path in sets.items() if path is None]:
        raise SystemExit(f"folder not found for {', '.join(missing)}: pass --{missing[0]} or set PACKAGE_DIR")
    benchmark = await start_benchmark(
        str(owner.id), args.name, sets, service, runner,
        answer_key=_default(args.answer_key, DEFAULT_ANSWER_KEY, file=True),
        preliminary=_default(args.preliminary, DEFAULT_PRELIMINARY, file=True),
        repeats=args.repeats, projects=args.projects,
    )
    for error in benchmark.errors:
        print("!", error)
    while benchmark.status != "concluido":
        counts = progress(benchmark, await analyses_of(benchmark))
        print(f"[benchmark {benchmark.id}] {counts['concluida'] + counts['falhou']}/{len(benchmark.runs)} · "
              f"rodando {counts['rodando']} · falhas {counts['falhou']}", flush=True)
        await asyncio.sleep(args.poll)
        benchmark = await refresh(await Benchmark.get(benchmark.id), service.catalog)
    await runner.wait_all()
    return benchmark


async def rejudge(args: argparse.Namespace, service: AnalysisService) -> Benchmark:
    source = await Benchmark.get(PydanticObjectId(args.rejudge))
    if source is None:
        raise SystemExit(f"benchmark not found: {args.rejudge}")
    options = JudgeOptions.from_settings(service.settings)
    benchmark = await create_rejudge(source, source.owner_id, service.models_by_role(), service.catalog, options,
                                     name=args.name if args.name != "benchmark" else None, projects=args.projects,
                                     repeats=args.repeats)
    for error in benchmark.errors:
        print("!", error)
    print(f"[re-julgar {benchmark.id}] origem {source.id} · {len(benchmark.runs)} análises · {options.model_dump()}",
          flush=True)
    return await run_rejudge(benchmark, service.llm, service.catalog, options, settings.analysis_concurrency)


async def _main(args: argparse.Namespace) -> None:
    await init_db()
    await seed_users()
    await sync_catalog_to_db(get_catalog())
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            llm = LLMClient(settings)
            service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
            if args.rejudge:
                benchmark = await rejudge(args, service)
            else:
                benchmark = await run(args, service, JobRunner(settings.analysis_concurrency))
        if benchmark.metrics:
            print_summary(benchmark.metrics)
        print(f"\nsalvo no Mongo: benchmark {benchmark.id} (GET /benchmarks/{benchmark.id})")
        if args.out:
            counts = progress(benchmark, await analyses_of(benchmark))
            payload = BenchmarkRead.of(benchmark, counts).model_dump(mode="json")
            payload["headline"] = headline(benchmark.metrics) if benchmark.metrics else {}
            args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"métricas em {args.out}")
    finally:
        await close_db()


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark the pipeline: accuracy, time, LLM cost, gates, determinism")
    parser.add_argument("--name", default="benchmark")
    parser.add_argument("--sets", nargs="+", choices=list(DEFAULT_DIRS), default=list(DEFAULT_DIRS))
    parser.add_argument("--historico", type=Path, help=f"default: PACKAGE_DIR/{DEFAULT_DIRS['historico']}")
    parser.add_argument("--analise", type=Path, help=f"default: PACKAGE_DIR/{DEFAULT_DIRS['analise']}")
    parser.add_argument("--answer-key", type=Path, help=f"default: PACKAGE_DIR/{DEFAULT_ANSWER_KEY}")
    parser.add_argument("--preliminary", type=Path, help=f"default: PACKAGE_DIR/{DEFAULT_PRELIMINARY} (not official)")
    parser.add_argument("--repeats", type=int, default=1, help="runs per project (≥ 2 measures determinism)")
    parser.add_argument("--projects", type=lambda v: [c.strip() for c in v.split(",") if c.strip()], default=[],
                        help="only these codes, e.g. PRJ01,PRJ21")
    parser.add_argument("--owner", default=settings.seed_email_pattern.format(n=1), help="analyst e-mail")
    parser.add_argument("--poll", type=float, default=10, help="seconds between progress lines")
    parser.add_argument("--out", type=Path, help="also write the metrics as JSON")
    parser.add_argument("--rejudge", metavar="BENCHMARK_ID",
                        help="re-run only judge → gates → class over the finished analyses of this benchmark")
    return parser


def main() -> None:
    cli = parser()
    args = cli.parse_args()
    if args.repeats < 1:
        cli.error("--repeats must be ≥ 1")
    asyncio.run(_main(args))
