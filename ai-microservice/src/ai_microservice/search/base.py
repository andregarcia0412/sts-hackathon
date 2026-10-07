import hashlib
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, Field

DateSource = Literal["metadata", "page", "unknown"]


def source_id(key: str) -> str:
    """ID curto e estável de uma fonte (derivado do DOI/URL), usado para citar evidências."""
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
        """Busca documentos. Provedores que filtram por data na origem devolvem só o que é anterior a `before`."""
        ...

    async def enrich(self, hit: SearchHit) -> SearchHit:
        """Completa conteúdo e data de publicação quando a busca não traz metadados (ex.: páginas web)."""
        ...
