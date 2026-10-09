from datetime import date

from backend.llm import WebPage, WebSearchResult
from backend.search.ollama_web import OllamaWebProvider, PageDate
from tests.fakes import FakeLLM


async def test_search_restricts_to_site_and_maps_hits():
    llm = FakeLLM()
    llm.search_results = [WebSearchResult(title="Patent", url="https://patents.google.com/x", content="claims")]
    hits = await OllamaWebProvider(llm, name="google_patents", site="patents.google.com").search(
        "load shedding", before=date(2025, 1, 1), limit=3
    )
    assert llm.searches == ["load shedding site:patents.google.com"]
    assert hits[0].provider == "google_patents"
    assert hits[0].snippet == "claims"


async def test_enrich_reads_page_date_from_llm():
    llm = FakeLLM({PageDate: PageDate(data="2018-05-01", tipo="publicacao", trecho="Published May 1, 2018")})
    llm.pages["https://a.test"] = WebPage(url="https://a.test", title="A", content="Published May 1, 2018 body")
    provider = OllamaWebProvider(llm, name="web")
    [hit] = [h for h in [await provider.enrich(_hit("https://a.test"))]]
    assert hit.published_date == date(2018, 5, 1)
    assert hit.date_source == "page"
    assert "Published" in hit.snippet


async def test_enrich_without_date_keeps_unknown():
    llm = FakeLLM({PageDate: PageDate(data=None, tipo="desconhecida", trecho="")})
    llm.pages["https://a.test"] = WebPage(url="https://a.test", title="A", content="no date here")
    hit = await OllamaWebProvider(llm, name="web").enrich(_hit("https://a.test"))
    assert hit.published_date is None
    assert hit.date_source == "unknown"


def _hit(url):
    from backend.search.base import SearchHit, source_id

    return SearchHit(id=source_id(url), provider="web", title="t", url=url)
