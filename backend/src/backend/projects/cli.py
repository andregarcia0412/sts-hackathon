"""`uv run backend-import <folder>`: imports every project folder found and analyses them as a batch."""

import argparse
import asyncio
from pathlib import Path

import httpx

from backend.analyses.batch import batch_panel, groups_from_directory, import_projects
from backend.analyses.jobs import JobRunner
from backend.analyses.orchestrator import AnalysisService
from backend.analyses.schemas import BatchRead
from backend.catalog.loader import get_catalog, sync_catalog_to_db
from backend.config import settings
from backend.database import close_db, init_db
from backend.llm import LLMClient
from backend.search.providers import build_providers
from backend.users.seed import seed_users
from backend.users.service import get_user_by_email


async def run_import(root: Path, owner_email: str, service: AnalysisService, runner, poll_s: float = 5) -> BatchRead:
    owner = await get_user_by_email(owner_email)
    if owner is None:
        raise SystemExit(f"user not found: {owner_email}")
    groups = groups_from_directory(root)
    if not groups:
        raise SystemExit(f"no project folder (evidence inventory) found under {root}")
    batch = await import_projects(groups, str(owner.id), root.name, service, runner)
    while True:
        panel = await batch_panel(batch)
        done = panel.counts["concluida"] + panel.counts["falhou"]
        print(f"[lote {panel.name}] {done}/{panel.total} concluídos · rodando {panel.counts['rodando']} · "
              f"falhas {panel.counts['falhou']}", flush=True)
        if done == panel.total:
            break
        await asyncio.sleep(poll_s)
    await runner.wait_all()
    for item in panel.items:
        print(f"  {item.code or item.project_name:8} {item.status:10} {item.suggested_class or '-':24} "
              f"{'inconsistente' if item.inconsistent else ''} {item.total_s or '-'} s  análise={item.analysis_id}")
    return panel


async def _main(root: Path, owner_email: str) -> None:
    await init_db()
    await seed_users()
    await sync_catalog_to_db(get_catalog())
    async with httpx.AsyncClient(timeout=30) as http:
        llm = LLMClient(settings)
        service = AnalysisService(llm, lambda: build_providers(llm, http, settings), settings, get_catalog())
        try:
            await run_import(root, owner_email, service, JobRunner(settings.analysis_concurrency))
        finally:
            await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and analyse project folders as a batch")
    parser.add_argument("folder", type=Path, help="package folder (or one project folder)")
    parser.add_argument("--owner", default=settings.seed_email_pattern.format(n=1), help="analyst e-mail")
    args = parser.parse_args()
    asyncio.run(_main(args.folder.resolve(), args.owner))
