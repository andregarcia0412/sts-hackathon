import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.routing import route_fragments
from tests.factories import synthetic_canonical


@pytest.fixture
async def canonical():
    return await synthetic_canonical()


async def test_routes_by_file_type_and_anchor(canonical):
    catalog = get_catalog()
    routed = route_fragments(canonical, [catalog.get("NOV-D1"), catalog.get("NOV-D6")], max_table_rows=50)
    ids = [f.id for f in routed.fragments]
    assert "PRJ90-EV06#2" in ids
    assert "PRJ90-EV06#1" in ids  # NOV-D6 -> metodo#1
    assert "PRJ90-S02" in ids and "PRJ90-S01-M001" in ids
    assert "PRJ90-EV06#3" not in ids
    assert len(ids) == len(set(ids))


async def test_testimony_is_never_routed_as_evidence_but_kept_apart(canonical):
    routed = route_fragments(canonical, get_catalog().rules_for("NOV", "doc"), max_table_rows=50)
    assert all(f.nature != "depoimento" for f in routed.fragments)
    assert {f.anchor for f in routed.testimony} >= {"conclusao"}


async def test_large_tables_are_capped_with_a_note(canonical):
    routed = route_fragments(canonical, [get_catalog().get("REP-D9")], max_table_rows=1)
    assert sum(f.file_type == "medicoes" for f in routed.fragments) == 1
    assert any("medicoes" in note for note in routed.truncated)
