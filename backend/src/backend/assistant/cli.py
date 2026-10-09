"""`uv run backend-ingest-norms`: (re)indexes the normative PDFs of NORMS_DIR."""

import asyncio

from backend.assistant.norms import ingest_norms
from backend.config import settings
from backend.database import close_db, init_db


async def _main() -> None:
    await init_db()
    try:
        chunks = await ingest_norms(settings.norms_dir)
        norms = sorted({c.norm for c in chunks})
        print(f"{len(chunks)} trechos indexados de {len(norms)} normas em {settings.norms_dir}:")
        for norm in norms:
            print(f"  {norm}: {sum(c.norm == norm for c in chunks)} trechos")
    finally:
        await close_db()


def main() -> None:
    asyncio.run(_main())
