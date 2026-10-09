import hashlib
from datetime import UTC, date, datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from backend.search.base import SearchHit, SearchProvider


class SearchCacheEntry(Document):
    """`query → result` shared by every web sub-agent (reproducibility and rate limits)."""

    key: Annotated[str, Indexed(unique=True)]
    kind: str  # "search" | "enrich"
    provider: str
    query: str
    hits: list[SearchHit]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "search_cache"


def _key(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


class CachedProvider:
    """Wraps a provider: identical searches (and page enrichments) are served from Mongo."""

    def __init__(self, inner: SearchProvider) -> None:
        self._inner = inner
        self.name = inner.name

    async def search(self, query: str, before: date, limit: int) -> list[SearchHit]:
        key = _key("search", self.name, query.strip().lower(), before.isoformat(), limit)
        if cached := await SearchCacheEntry.find_one(SearchCacheEntry.key == key):
            return cached.hits
        hits = await self._inner.search(query, before=before, limit=limit)
        await _store(key, "search", self.name, query, hits)
        return hits

    async def enrich(self, hit: SearchHit) -> SearchHit:
        key = _key("enrich", self.name, hit.url)
        if cached := await SearchCacheEntry.find_one(SearchCacheEntry.key == key):
            return cached.hits[0]
        enriched = await self._inner.enrich(hit)
        await _store(key, "enrich", self.name, hit.url, [enriched])
        return enriched


async def _store(key: str, kind: str, provider: str, query: str, hits: list[SearchHit]) -> None:
    entry = SearchCacheEntry(key=key, kind=kind, provider=provider, query=query, hits=hits)
    try:
        await entry.insert()
    except Exception:  # a concurrent run stored the same key first: the cached value is equivalent
        pass
