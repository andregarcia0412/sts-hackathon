"""`uv run backend-entrega run|export`: the delivery of the 20 cases (spec 08).

    uv run backend-entrega run [--projects PRJ21,PRJ22] [--resume <benchmark_id>] [--yes]
    (analysts review and decide in the front: POST /projects/{id}/decisions)
    uv run backend-entrega export <benchmark_id> [--out <folder outside the repo>] [--zip] [--require-decisions]
"""

import argparse
import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

import httpx

from backend.analyses.jobs import JobRunner
from backend.analyses.orchestrator import AnalysisService
from backend.benchmark.cli import print_summary
from backend.benchmark.router import DEFAULT_DIRS, DEFAULT_PRELIMINARY
from backend.benchmark.service import analyses_of, progress, refresh
from backend.catalog.loader import get_catalog, sync_catalog_to_db
from backend.config import settings
from backend.database import close_db, init_db
from backend.delivery.export import DeliveryError, export_delivery
from backend.delivery.run import estimate, get_benchmark, last_finished_benchmark, pending_codes, run_delivery
from backend.llm import LLMClient
from backend.search.providers import build_providers
from backend.users.seed import seed_users
from backend.users.service import get_user_by_email


def default_out() -> Path:
    base = (settings.package_dir.parent if settings.package_dir else Path.home()) / "entregas"
    return base / f"entrega_{datetime.now():%Y-%m-%d_%H%M}"


async def _run(args: argparse.Namespace) -> int:
    await seed_users()
    await sync_catalog_to_db(get_catalog())
    owner = await get_user_by_email(args.owner)
    if owner is None:
        raise SystemExit(f"user not found: {args.owner}")
    folder = args.folder or (settings.package_dir / DEFAULT_DIRS["analise"] if settings.package_dir else None)
    if folder is None or not folder.is_dir():
        raise SystemExit("cases folder not found: pass --folder or set PACKAGE_DIR")
    resume = await get_benchmark(args.resume) if args.resume else None
    todo, reused = await pending_codes(folder, resume, get_catalog().versao, args.projects)
    print(f"a analisar: {', '.join(todo) or '-'}" + (f" · reaproveitados: {', '.join(reused)}" if reused else ""))
    print("estimativa:", estimate(len(todo), settings.analysis_concurrency, await last_finished_benchmark(str(owner.id))))
    if todo and not args.yes and input("continuar? [s/N] ").strip().lower() not in ("s", "sim", "y", "yes"):
        return 1
    preliminary = settings.package_dir / DEFAULT_PRELIMINARY if settings.package_dir else None
    async with httpx.AsyncClient(timeout=30) as http:
        llm = LLMClient(settings)
        service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
        runner = JobRunner(settings.analysis_concurrency)
        benchmark = await run_delivery(str(owner.id), args.name, folder, service, runner,
                                       preliminary if preliminary and preliminary.is_file() else None,
                                       args.projects, resume)
        while benchmark.status != "concluido":
            counts = progress(benchmark, await analyses_of(benchmark))
            print(f"[entrega {benchmark.id}] {counts['concluida'] + counts['falhou']}/{len(benchmark.runs)} · "
                  f"rodando {counts['rodando']} · falhas {counts['falhou']}", flush=True)
            await asyncio.sleep(args.poll)
            benchmark = await refresh(await get_benchmark(str(benchmark.id)), service.catalog)
        await runner.wait_all()
    if benchmark.metrics:
        print_summary(benchmark.metrics)
    print(f"\nbenchmark da entrega: {benchmark.id} → uv run backend-entrega export {benchmark.id}")
    return 0


async def _export(args: argparse.Namespace) -> int:
    benchmark = await get_benchmark(args.benchmark)
    if benchmark is None:
        raise SystemExit(f"benchmark not found: {args.benchmark}")
    out = args.out or default_out()
    try:
        result = await export_delivery(benchmark, get_catalog(), out, expected=args.expected,
                                       require_decisions=args.require_decisions)
    except DeliveryError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    for project in result.projects:
        mark = "ok" if project.status == "ok" else "FALHOU"
        notes = "; ".join(project.warnings + ([project.error] if project.error else []))
        print(f"{project.code:6} {mark:6} {project.suggested_class or '-':24} {notes}")
    if args.zip:
        archive = shutil.make_archive(str(out), "zip", root_dir=out)
        print(f"zip: {archive}")
    print(f"\nentrega em {result.folder} ({'completa' if result.ok else 'com falhas: veja manifest.json'})")
    return 0 if result.ok else 1


async def _main(args: argparse.Namespace) -> int:
    await init_db()
    try:
        return await (_run(args) if args.command == "run" else _export(args))
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(prog="backend-entrega", description="Delivery of the cases for analysis")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="analyse the cases (resumable)")
    run.add_argument("--folder", type=Path, help=f"default: PACKAGE_DIR/{DEFAULT_DIRS['analise']}")
    run.add_argument("--projects", type=lambda v: [c.strip() for c in v.split(",") if c.strip()], default=[])
    run.add_argument("--resume", metavar="BENCHMARK_ID", help="reuse the unchanged finished analyses of a benchmark")
    run.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    run.add_argument("--name", default="entrega")
    run.add_argument("--owner", default=settings.seed_email_pattern.format(n=1))
    run.add_argument("--poll", type=float, default=30)
    export = sub.add_parser("export", help="write the delivery folder from what is in Mongo")
    export.add_argument("benchmark")
    export.add_argument("--out", type=Path, help="default: PACKAGE_DIR/../entregas/entrega_<date>; never in the repo")
    export.add_argument("--zip", action="store_true")
    export.add_argument("--require-decisions", action="store_true", help="fail if a project has no analyst decision")
    export.add_argument("--expected", type=int, default=20, help="projects expected in the delivery")
    sys.exit(asyncio.run(_main(parser.parse_args())))
