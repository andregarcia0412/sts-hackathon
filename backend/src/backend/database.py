from beanie import init_beanie
from pymongo import AsyncMongoClient

from backend.config import settings
from backend.models import DOCUMENT_MODELS

client: AsyncMongoClient | None = None


async def init_db() -> None:
    global client
    client = AsyncMongoClient(settings.mongodb_uri)
    await init_beanie(
        database=client[settings.mongodb_db],
        document_models=DOCUMENT_MODELS,
    )


async def close_db() -> None:
    if client is not None:
        await client.close()


async def ping_db() -> bool:
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False
