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
