from datetime import date

from backend.search.base import SearchHit
from backend.search.cache import CachedProvider
from tests.fakes import FakeSearchProvider


def hit(n: int) -> SearchHit:
    return SearchHit(id=f"src-{n}", provider="fake", title=f"T{n}", url=f"https://x.test/{n}")


async def test_second_identical_search_comes_from_cache(db):
    inner = FakeSearchProvider("fake", [hit(1), hit(2)])
    provider = CachedProvider(inner)
    first = await provider.search("q", before=date(2025, 1, 1), limit=5)
    second = await provider.search("q", before=date(2025, 1, 1), limit=5)
    assert first == second
    assert inner.queries == ["q"]
    assert provider.name == "fake"


async def test_different_reference_date_is_a_different_entry(db):
    inner = FakeSearchProvider("fake", [hit(1)])
    provider = CachedProvider(inner)
    await provider.search("q", before=date(2025, 1, 1), limit=5)
    await provider.search("q", before=date(2024, 1, 1), limit=5)
    assert inner.queries == ["q", "q"]


async def test_errors_are_not_cached(db):
    inner = FakeSearchProvider("fake", error=RuntimeError("down"))
    provider = CachedProvider(inner)
    for _ in range(2):
        try:
            await provider.search("q", before=date(2025, 1, 1), limit=5)
        except RuntimeError:
            pass
    assert inner.queries == ["q", "q"]
