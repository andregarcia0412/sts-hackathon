from datetime import date

import httpx

from ai_microservice.search.base import SearchHit, source_id

OPENALEX_URL = "https://api.openalex.org/works"


def rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions = {pos: word for word, indexes in inverted_index.items() for pos in indexes}
    return " ".join(positions[pos] for pos in sorted(positions))


class OpenAlexProvider:
    name = "openalex"

    def __init__(self, http: httpx.AsyncClient, api_key: str | None = None, mailto: str | None = None) -> None:
        self._http = http
        self._api_key = api_key
        self._mailto = mailto

    async def search(self, query: str, before: date, limit: int) -> list[SearchHit]:
        params: dict[str, str | int] = {
            "search": query,
            "filter": f"to_publication_date:{before.isoformat()}",
            "per_page": limit,
            "select": "id,doi,title,publication_date,abstract_inverted_index,primary_location,type",
        }
        if self._api_key:
            params["api_key"] = self._api_key
        if self._mailto:
            params["mailto"] = self._mailto
        response = await self._http.get(OPENALEX_URL, params=params)
        response.raise_for_status()
        return [self._to_hit(work) for work in response.json().get("results", [])]

    async def enrich(self, hit: SearchHit) -> SearchHit:
        return hit

    def _to_hit(self, work: dict) -> SearchHit:
        url = work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or work["id"]
        published = work.get("publication_date")
        return SearchHit(
            id=source_id(work.get("doi") or work["id"]),
            provider=self.name,
            title=work.get("title") or "(sem título)",
            url=url,
            snippet=rebuild_abstract(work.get("abstract_inverted_index")),
            published_date=date.fromisoformat(published) if published else None,
            date_source="metadata" if published else "unknown",
            extra={"openalex_id": work["id"], "tipo": work.get("type") or ""},
        )
