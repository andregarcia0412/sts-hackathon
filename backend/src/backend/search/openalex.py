import asyncio
import email.utils
from datetime import UTC, date, datetime

import httpx

from backend.search.base import SearchHit, source_id

OPENALEX_URL = "https://api.openalex.org/works"
MAX_RETRY_AFTER_S = 60.0


def retry_after_seconds(value: str | None, default: float) -> float | None:
    """`Retry-After` in seconds or as an HTTP date; None when longer than the cap (a daily budget is exhausted:
    waiting would only slow the analysis down — fail now, the error is logged and never cached)."""
    if not value:
        return default
    try:
        seconds = float(value)
    except ValueError:
        try:
            moment = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return default
        seconds = (moment - datetime.now(UTC)).total_seconds()
    return None if seconds > MAX_RETRY_AFTER_S else max(0.0, seconds)


def rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions = {pos: word for word, indexes in inverted_index.items() for pos in indexes}
    return " ".join(positions[pos] for pos in sorted(positions))


class OpenAlexProvider:
    """Scientific literature front (NOV-W2). Filters by publication date at the source (T3)."""

    name = "openalex"

    def __init__(self, http: httpx.AsyncClient, api_key: str | None = None, mailto: str | None = None,
                 retries: int = 2, max_concurrency: int = 2, backoff_s: float = 2.0) -> None:
        self._http = http
        self._api_key = api_key
        self._mailto = mailto  # the "polite pool": far fewer 429s in batch runs
        self._retries, self._backoff_s = retries, backoff_s
        self._semaphore = asyncio.Semaphore(max_concurrency)

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
        for attempt in range(1, self._retries + 2):
            async with self._semaphore:
                response = await self._http.get(OPENALEX_URL, params=params)
            if response.status_code != 429 or attempt > self._retries:
                break
            wait = retry_after_seconds(response.headers.get("Retry-After"), self._backoff_s * attempt)
            if wait is None:
                break  # budget exhausted for hours (no OPENALEX_API_KEY?): do not hold the analysis
            await asyncio.sleep(wait)  # rate limited: wait what the server asks (outside the semaphore), try again
        response.raise_for_status()  # an error is never cached as an empty result (CachedProvider stores successes)
        return [self._to_hit(work) for work in response.json().get("results", [])]

    async def enrich(self, hit: SearchHit) -> SearchHit:
        return hit

    def _to_hit(self, work: dict) -> SearchHit:
        url = work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or work["id"]
        published = work.get("publication_date")
        return SearchHit(
            id=source_id(work.get("doi") or work["id"]),
            provider=self.name,
            title=work.get("title") or "(untitled)",
            url=url,
            snippet=rebuild_abstract(work.get("abstract_inverted_index")),
            published_date=date.fromisoformat(published) if published else None,
            date_source="metadata" if published else "unknown",
            extra={"openalex_id": work["id"], "type": work.get("type") or ""},
        )
