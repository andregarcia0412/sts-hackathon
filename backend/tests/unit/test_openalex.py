from datetime import date

import httpx
import respx

from backend.search.openalex import OPENALEX_URL, OpenAlexProvider, rebuild_abstract


def test_rebuild_abstract_orders_words_by_position():
    assert rebuild_abstract({"breaker": [1], "circuit": [0], "pattern": [2]}) == "circuit breaker pattern"
    assert rebuild_abstract(None) == ""


@respx.mock
async def test_search_filters_by_reference_date_and_maps_hits():
    route = respx.get(OPENALEX_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "doi": "https://doi.org/10.1/abc",
                        "title": "Bulkheads for microservices",
                        "publication_date": "2019-04-02",
                        "abstract_inverted_index": {"isolate": [0], "dependencies": [1]},
                        "type": "article",
                    }
                ]
            },
        )
    )
    async with httpx.AsyncClient() as http:
        hits = await OpenAlexProvider(http, mailto="x@y.z").search("bulkhead", before=date(2025, 1, 6), limit=5)

    params = route.calls.last.request.url.params
    assert params["filter"] == "to_publication_date:2025-01-06"
    assert params["mailto"] == "x@y.z"
    [hit] = hits
    assert hit.url == "https://doi.org/10.1/abc"
    assert hit.published_date == date(2019, 4, 2)
    assert hit.date_source == "metadata"
    assert hit.snippet == "isolate dependencies"


@respx.mock
async def test_rate_limit_waits_for_retry_after_and_tries_again(monkeypatch):
    import asyncio

    waits = []

    async def no_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    route = respx.get(OPENALEX_URL).mock(side_effect=[
        httpx.Response(429, headers={"Retry-After": "3"}),
        httpx.Response(200, json={"results": [{"id": "https://openalex.org/W1", "title": "Ok"}]}),
    ])
    async with httpx.AsyncClient() as http:
        hits = await OpenAlexProvider(http, retries=2).search("q", before=date(2025, 1, 6), limit=5)
    assert [h.title for h in hits] == ["Ok"] and route.call_count == 2 and waits == [3.0]


@respx.mock
async def test_rate_limit_gives_up_after_the_retries():
    import pytest

    respx.get(OPENALEX_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "0"}))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.HTTPStatusError):
            await OpenAlexProvider(http, retries=1).search("q", before=date(2025, 1, 6), limit=5)


@respx.mock
async def test_an_exhausted_daily_budget_fails_at_once(monkeypatch):
    import asyncio

    import pytest

    waits = []

    async def no_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    route = respx.get(OPENALEX_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "67966"}))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.HTTPStatusError):
            await OpenAlexProvider(http, retries=2).search("q", before=date(2025, 1, 6), limit=5)
    assert route.call_count == 1 and waits == []
