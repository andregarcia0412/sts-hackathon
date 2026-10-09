import asyncio
from datetime import date

from backend.criteria.web_sub import PlannedQuery, WebSub
from backend.search.base import SearchHit
from backend.search.grounding import domain_terms, grounded
from backend.search.session import SearchSession
from tests.factories import synthetic_canonical
from tests.fakes import FakeSearchProvider


async def test_domain_terms_come_from_the_project_and_never_carry_codes_or_numbers():
    terms = domain_terms(await synthetic_canonical())
    assert {"depen", "lotes", "batch", "queue"} <= terms
    assert not any(t.startswith("prj") or any(c.isdigit() for c in t) for t in terms)
    assert not any("concil" in t and "time" in t for t in terms)


async def test_ungrounded_query_never_reaches_the_provider():
    canonical = await synthetic_canonical()
    terms = domain_terms(canonical)
    assert grounded("dependency aware batch scheduling", terms)
    assert not grounded("Internet of Things Wikipedia", terms)
    assert not grounded("open problem in quantum error correction", terms)
    provider = FakeSearchProvider("openalex")
    sub = WebSub(None, None, "NOV", [], canonical, {"literatura": provider}, 3, 5, 6, None)
    entry, hits = await sub._search(PlannedQuery(frente="literatura", query="Internet of Things Wikipedia", regras=[]))
    assert provider.queries == [] and hits == [] and "sem termo do domínio" in entry.error
    assert entry.original_query == "Internet of Things Wikipedia"  # the log keeps it (T6)


async def test_near_identical_queries_of_the_same_front_share_one_call():
    canonical = await synthetic_canonical()
    hit = SearchHit(id="p1", provider="openalex", title="t", url="https://x", snippet="s", published_date=date(2019, 1, 1))
    provider = FakeSearchProvider("openalex", [hit])
    session = SearchSession()
    nov = WebSub(None, None, "NOV", [], canonical, {"literatura": provider, "patentes": provider}, 3, 5, 6, None,
                 session=session)
    cri = WebSub(None, None, "CRI", [], canonical, {"literatura": provider, "patentes": provider}, 3, 5, 6, None,
                 session=session)
    first, second = await asyncio.gather(
        nov._search(PlannedQuery(frente="literatura", query="deduplication by batch dependency queue patent", regras=[])),
        cri._search(PlannedQuery(frente="literatura", query="deduplication by batch dependency queue window patent",
                                 regras=[])))
    assert len(provider.queries) == 1
    assert [e.reused_from is None for e in (first[0], second[0])].count(True) == 1
    assert first[1] == second[1] == [hit]
    other_front, _ = await cri._search(PlannedQuery(frente="patentes", query="deduplication by batch dependency queue patent",
                                                    regras=[]))
    assert other_front.reused_from is None and len(provider.queries) == 2  # another front is never reused


async def test_a_repeated_url_is_fetched_once():
    calls = []

    async def fetch():
        calls.append(1)
        await asyncio.sleep(0)
        return "page"

    session = SearchSession()
    assert await asyncio.gather(session.page("https://x", fetch), session.page("https://x", fetch)) == ["page", "page"]
    assert len(calls) == 1


async def test_a_failed_search_is_reported_to_every_waiter_and_not_cached_as_empty():
    session = SearchSession()

    async def boom():
        raise RuntimeError("429")

    import pytest

    with pytest.raises(RuntimeError):
        await session.search("literatura", "a b c", boom)
    with pytest.raises(RuntimeError):
        await session.search("literatura", "a b c", boom)


def test_acronyms_written_in_the_project_ground_a_query():
    from backend.extraction.schema import CanonicalProject, ProjectContext

    canonical = CanonicalProject(project_code="PRJ90", files=[], fragments=[],
                                 context=ProjectContext(palavras_chave_pt=["respostas com RAG sobre documentos"]))
    terms = domain_terms(canonical)
    assert grounded("RAG citation grounding", terms)
    assert not grounded("TRL maturity assessment academic research", terms)
    assert not grounded("technical barrier solution availability literature", terms)
