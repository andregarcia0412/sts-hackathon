import hashlib
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, Field

DateSource = Literal["metadata", "page", "unknown"]


def source_id(key: str) -> str:
    """Short, stable id of a web source (derived from DOI/URL), used to cite evidence."""
    return "src-" + hashlib.sha1(key.strip().lower().encode()).hexdigest()[:10]


class SearchHit(BaseModel):
    id: str
    provider: str
    title: str
    url: str
    snippet: str = ""
    published_date: date | None = None
    date_source: DateSource = "unknown"
    extra: dict[str, str] = Field(default_factory=dict)


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, before: date, limit: int) -> list[SearchHit]:
        """Finds documents. Providers that filter by date at the source only return what precedes `before`."""
        ...

    async def enrich(self, hit: SearchHit) -> SearchHit:
        """Fills content and publication date when the search has no metadata (e.g. web pages)."""
        ...
