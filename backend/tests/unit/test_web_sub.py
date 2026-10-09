from datetime import date

import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.schemas import ClosestDoc
from backend.criteria.web_sub import QueryPlanOut, WebJudgeOut, run_web_sub
from backend.search.base import SearchHit
from tests.factories import synthetic_canonical
from tests.fakes import FakeLLM, FakeSearchProvider, user_text

PRIOR = SearchHit(id="src-old", provider="openalex", title="Dependency-aware queues", url="https://doi.org/1",
                  snippet="Batches are ordered by a dependency graph of shared balances.", published_date=date(2019, 1, 1),
                  date_source="metadata")
LATER = SearchHit(id="src-new", provider="web", title="New scheduler", url="https://x.test/new",
                  snippet="A dependency graph scheduler for ledgers.", published_date=date(2025, 6, 1), date_source="page")
UNDATED = SearchHit(id="src-nodate", provider="web", title="Blog", url="https://x.test/blog", snippet="FIFO fails here.")


def plan(_):
    return QueryPlanOut(queries=[
        {"frente": "literatura", "query": "PRJ90 Time Conciliacao dependency batch scheduling", "regras": ["NOV-W3"]},
        {"frente": "mercado", "query": "ledger batch scheduler 98%", "regras": ["NOV-W4"]},
        {"frente": "mercado", "query": "PRJ90", "regras": ["NOV-W4"]},
    ])


def judge(_):
    return WebJudgeOut(
        evidencias=[
            {"regra_id": "NOV-W3", "fonte_id": "src-old", "quote": "ordered by a dependency graph", "polaridade": "negativa", "justificativa": "cobre"},
            {"regra_id": "NOV-W3", "fonte_id": "src-new", "quote": "dependency graph scheduler", "polaridade": "negativa", "justificativa": "posterior"},
            {"regra_id": "NOV-W6", "fonte_id": "src-new", "quote": "dependency graph scheduler", "polaridade": "positiva", "justificativa": "simultâneo"},
            {"regra_id": "NOV-W4", "fonte_id": "src-old", "quote": "texto inventado", "polaridade": "negativa", "justificativa": "x"},
        ],
        regras_sem_evidencia=[{"regra_id": "NOV-W5", "motivo": "nenhuma fonte sobre método"}],
        documento_mais_proximo={"fonte_id": "src-old", "cobertura": "total", "o_que_o_projeto_tem_a_mais": "nada"},
    )


@pytest.fixture
async def canonical():
    return await synthetic_canonical()


def providers(error=None):
    return {
        "literatura": FakeSearchProvider("openalex", [PRIOR], error=error),
        "patentes": FakeSearchProvider("google_patents", [], error=error),
        "mercado": FakeSearchProvider("ollama_web", [LATER, UNDATED], error=error),
        "documentacao": FakeSearchProvider("ollama_web_docs", [], error=error),
    }


async def run(canonical, prov, criterion="NOV", closest=None, judge_handler=judge):
    catalog = get_catalog()
    llm = FakeLLM({QueryPlanOut: plan, WebJudgeOut: judge_handler})
    result = await run_web_sub(llm, catalog, criterion, catalog.rules_for(criterion, "web"), canonical, prov,
                               queries_per_front=2, results_per_query=5, fetch_per_front=4, closest_doc=closest)
    return result, llm


async def test_queries_are_sanitized_before_leaving(canonical):
    prov = providers()
    result, _ = await run(canonical, prov)
    assert prov["literatura"].queries == ["dependency batch scheduling"]
    assert prov["mercado"].queries == ["ledger batch scheduler"]
    entry = next(e for e in result.search_log if e.base == "openalex")
    assert entry.original_query.startswith("PRJ90 Time Conciliacao")
    assert entry.sanitized_query == "dependency batch scheduling"
    assert any(e.error and "vazia" in e.error for e in result.search_log)


async def test_sources_are_dated_against_the_reference_date(canonical):
    result, _ = await run(canonical, providers())
    by_id = {s.id: s for s in result.web_sources}
    assert by_id["src-old"].prior_art is True
    assert by_id["src-new"].prior_art is False
    assert by_id["src-nodate"].prior_art is None
    assert by_id["src-nodate"].date_label == "data indeterminada"
    assert by_id["src-new"].date_label == "não é estado da arte"


async def test_later_sources_only_count_for_nov_w6_and_quotes_are_gated(canonical):
    result, _ = await run(canonical, providers())
    runs = {r.rule_id: r for r in result.rules}
    assert [e.source_id for e in runs["NOV-W3"].evidences] == ["src-old"]
    assert [e.source_id for e in runs["NOV-W6"].evidences] == ["src-new"]
    assert runs["NOV-W4"].status == "sem_evidencia"
    assert runs["NOV-W5"].reason == "nenhuma fonte sobre método"
    evidence = runs["NOV-W3"].evidences[0]
    assert evidence.origin == "web" and evidence.url == "https://doi.org/1"
    assert evidence.query == "dependency batch scheduling"


async def test_closest_document_reported_for_novelty(canonical):
    result, _ = await run(canonical, providers())
    assert result.closest_doc.source_id == "src-old"
    assert result.closest_doc.cobertura == "total"


async def test_procedural_rules(canonical):
    result, _ = await run(canonical, providers())
    runs = {r.rule_id: r for r in result.rules}
    assert runs["NOV-W1"].status == "executada"
    assert "2025-01-06" in runs["NOV-W1"].note
    assert runs["NOV-W2"].status == "executada"
    assert "patentes" in runs["NOV-W2"].note  # front without results is reported
    assert runs["NOV-W8"].status == "executada"


async def test_web_down_marks_rules_not_executed(canonical):
    result, _ = await run(canonical, providers(error=RuntimeError("offline")))
    runs = {r.rule_id: r for r in result.rules}
    assert runs["NOV-W3"].status == "nao_executada"
    assert "web" in runs["NOV-W3"].reason
    assert runs["NOV-W2"].status == "nao_executada"


async def test_closest_doc_of_novelty_goes_into_creativity_prompt(canonical):
    closest = ClosestDoc(source_id="src-old", title="Dependency-aware queues", url="https://doi.org/1",
                         cobertura="parcial", o_que_o_projeto_tem_a_mais="desempate", quote="")
    def judge_cri(_):
        return WebJudgeOut(evidencias=[], regras_sem_evidencia=[], documento_mais_proximo=None)
    _, llm = await run(canonical, providers(), criterion="CRI", closest=closest, judge_handler=judge_cri)
    assert "Dependency-aware queues" in user_text(llm.calls_for(WebJudgeOut)[0])
