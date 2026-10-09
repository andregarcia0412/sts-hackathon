import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.schemas import CriterionResult, Divergence, MissingLink, SearchLogEntry, WebSource
from backend.graph.builder import build_graph
from backend.graph.classify import classify
from backend.graph.models import GraphEdge, GraphNode
from backend.graph.queries import save_graph, trace
from backend.graph.scoring import score_rule
from backend.graph.states import CriterionState
from tests.factories import evidence, run, synthetic_canonical


@pytest.fixture
async def inputs():
    canonical = await synthetic_canonical()
    ev_doc = evidence("NOV-D2", source="PRJ90-EV06#1")
    ev_neg = evidence("NOV-D10", "negativa", source="PRJ90-EV06#2")
    from datetime import UTC, datetime
    web = WebSource(id="src-a", front="literatura", base="openalex", title="Paper", url="https://doi.org/a",
                    prior_art=True, date_label="estado da arte", snippet="s", captured_at=datetime.now(UTC))
    ev_web = evidence("NOV-W3", source="src-a", nature="web", origin="web")
    log = SearchLogEntry(criterion="NOV", front="literatura", base="openalex", original_query="PRJ90 q",
                         sanitized_query="q", executed_at=datetime.now(UTC), selected=["src-a"])
    results = {c: CriterionResult(criterion=c) for c in ("NOV", "CRI", "INC", "SIS", "REP")}
    results["NOV"] = CriterionResult(
        criterion="NOV",
        rules=[run("NOV-D2", ev_doc), run("NOV-D10", ev_neg), run("NOV-W3", ev_web), run("NOV-D8", status="na", reason="x")],
        divergences=[Divergence(criterion="NOV", testimony_fragment_id="PRJ90-EV10#conclusao", testimony_quote="t",
                                record_fragment_id="PRJ90-S02", record_alias="evidencias/resultados.csv#PRJ90-S02",
                                record_quote="r", statement="A entrevista afirma...")],
        missing_links=[MissingLink(criterion="NOV", description="MEMO", evidence_to_request="saída", fragment_ids=["PRJ90-EV13#declaracao_da_equipe"])],
        web_sources=[web],
        search_log=[log],
    )
    catalog = get_catalog()
    scores = {c: [score_rule(r, catalog.get(r.rule_id)) for r in res.rules] for c, res in results.items()}
    states = {c: CriterionState.of(c, v) for c, v in {
        "NOV": "NÃO DEMONSTRADA", "CRI": "NÃO DEMONSTRADA", "INC": "NÃO CARACTERIZADA",
        "SIS": "DOCUMENTADA COMO ACEITE", "REP": "DOCUMENTADA PARA A CONFIGURAÇÃO"}.items()}
    states["NOV"].decisive_evidence_ids = [ev_neg.id]
    return canonical, results, scores, states, classify(states), (ev_doc, ev_neg, ev_web)


async def test_builder_creates_typed_nodes_and_edges(inputs):
    canonical, results, scores, states, suggestion, (ev_doc, ev_neg, ev_web) = inputs
    nodes, edges = build_graph("an-1", canonical, get_catalog(), results, scores, states, suggestion)
    by_id = {n.node_id: n for n in nodes}
    assert by_id[f"evidence:{ev_doc.id}"].props["polarity"] == "positiva"
    assert by_id["rule:NOV-D2"].props["score"] == 100
    assert by_id["criterion:NOV"].props["state"] == "NÃO DEMONSTRADA"
    assert by_id["class:suggested"].props["suggested_class"] == "not_eligible"
    assert by_id["source:PRJ90-EV06#1"].props["alias"] == "evidencias/metodo.md#1"
    assert by_id["source:src-a"].props["url"] == "https://doi.org/a"
    kinds = {(e.source, e.kind, e.target) for e in edges}
    assert (f"evidence:{ev_doc.id}", "sustenta", "rule:NOV-D2") in kinds
    assert (f"evidence:{ev_neg.id}", "contraria", "rule:NOV-D10") in kinds
    assert (f"evidence:{ev_doc.id}", "cita", "source:PRJ90-EV06#1") in kinds
    assert ("rule:NOV-D2", "compoe", "criterion:NOV") in kinds
    assert ("criterion:NOV", "compoe", "class:suggested") in kinds
    assert (f"evidence:{ev_neg.id}", "decisiva", "criterion:NOV") in kinds
    divergence = next(n for n in nodes if n.kind == "divergence")
    assert any(e.source == divergence.node_id and e.props.get("prevalece") for e in edges)
    assert any(n.kind == "gap" for n in nodes)
    assert any(n.kind == "search" and n.props["sanitized_query"] == "q" for n in nodes)
    assert all(e.source in by_id and e.target in by_id for e in edges)


async def test_builder_is_deterministic(inputs):
    canonical, results, scores, states, suggestion, _ = inputs
    first = build_graph("an-1", canonical, get_catalog(), results, scores, states, suggestion)
    second = build_graph("an-1", canonical, get_catalog(), results, scores, states, suggestion)
    assert [n.node_id for n in first[0]] == [n.node_id for n in second[0]]


async def test_save_is_idempotent_and_trace_walks_to_sources(db, inputs):
    canonical, results, scores, states, suggestion, (ev_doc, ev_neg, ev_web) = inputs
    nodes, edges = build_graph("an-1", canonical, get_catalog(), results, scores, states, suggestion)
    await save_graph("an-1", nodes, edges)
    await save_graph("an-1", nodes, edges)
    assert await GraphNode.find(GraphNode.analysis_id == "an-1").count() == len(nodes)
    assert await GraphEdge.find(GraphEdge.analysis_id == "an-1").count() == len(edges)

    reached = await trace("an-1", "class:suggested")
    reached_ids = {n.node_id for n in reached}
    assert {"criterion:NOV", "rule:NOV-D2", f"evidence:{ev_doc.id}", "source:PRJ90-EV06#1", "source:src-a"} <= reached_ids
    assert await trace("an-2", "class:suggested") == []


async def test_coherence_record_becomes_a_node_linked_to_the_criterion(inputs):
    from backend.graph.coherence import Coherence

    canonical, results, scores, states, suggestion, (_, ev_neg, _) = inputs
    states["NOV"].coherence = Coherence(score=80, rules_with_evidence=5, strength="forte_positivo",
                                        original_state="INDETERMINADA", original_source="juiz", rejudged=True,
                                        status="resolvida")
    nodes, edges = build_graph("a1", canonical, get_catalog(), results, scores, states, suggestion)
    node = next(n for n in nodes if n.kind == "coherence")
    assert node.props["original_state"] == "INDETERMINADA" and node.props["final_state"] == "NÃO DEMONSTRADA"
    links = {(e.kind, e.target) for e in edges if e.source == node.node_id}
    assert ("afeta", "criterion:NOV") in links and ("cita", f"evidence:{ev_neg.id}") in links
