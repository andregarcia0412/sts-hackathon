"""`uv run backend-export-frontend [--out DIR] [--owner ID] [--project ID]` (spec 13).

Reads Mongo and writes one JSON per API route so the hifi front-end can run without the
backend (static mode). Default destination: `frontend-static/` at the repo root (its
contents are confidential: package excerpts) — it is git-ignored.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from backend.catalog.loader import get_catalog, sync_catalog_to_db
from backend.database import close_db, init_db
from backend.frontend_api.exporter import export_frontend


async def _main(out: Path, owner: str | None, project: str | None) -> int:
    await init_db()
    await sync_catalog_to_db(get_catalog())
    try:
        result = await export_frontend(out, owner=owner, project=project)
    finally:
        await close_db()
    print(f"[export] {len(result.projects)} projeto(s) → {result.folder}")
    for p in result.projects:
        print(f"  {p.code or p.name:24} análise={p.analysis_id or '-'}")
    print(f"[export] usuários, lista e manifest em {result.folder}/users.json, projects.json, manifest.json")
    return 0 if result.ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the front-end's static data from the database (spec 13).")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[3] / "frontend-static",
                        help="destination folder (default: frontend-static/ at the repo root)")
    parser.add_argument("--owner", help="export only this analyst's projects (user id)")
    parser.add_argument("--project", help="export a single project (id)")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.out, args.owner, args.project)))


if __name__ == "__main__":
    main()