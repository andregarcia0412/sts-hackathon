from datetime import date

from ai_microservice.modules.novelty.fronts import FrontAgent, find_sensitive_term
from ai_microservice.modules.novelty.schemas import DocComparison, QueryPlan
from ai_microservice.search.base import SearchHit
from tests.factories import make_profile
from tests.fakes import FakeLLM

COMPARISON = DocComparison(
    cobertura="parcial", o_que_o_projeto_tem_a_mais="", em_uso_no_setor="sim", metodo_publico="sim", resumo="r"
)


class FakeProvider:
    name = "fake"

    def __init__(self, hits_by_query: dict[str, list[SearchHit]]) -> None:
        self.hits_by_query = hits_by_query
        self.queries: list[str] = []

    async def search(self, query: str, before: date, limit: int) -> list[SearchHit]:
        self.queries.append(query)
        return self.hits_by_query.get(query, [])[:limit]

    async def enrich(self, hit: SearchHit) -> SearchHit:
        return hit


def hit(hit_id: str, published: date | None) -> SearchHit:
    return SearchHit(id=hit_id, provider="fake", title=hit_id, url=f"https://x/{hit_id}", published_date=published)


def make_agent(queries: list[str], provider: FakeProvider, max_docs: int = 10) -> tuple[FrontAgent, FakeLLM]:
    llm = FakeLLM({QueryPlan: lambda _: QueryPlan(queries=queries), DocComparison: lambda _: COMPARISON})
    return FrontAgent("mercado", provider, llm, queries=3, results_per_query=5, max_docs=max_docs), llm


def test_sensitive_term_match_ignores_case_and_accents():
    assert find_sensitive_term("runbook gw-7 circuit breaker", ["GW-7"]) == "GW-7"
    assert find_sensitive_term("plataforma de servicos gateway", ["Plataforma de Serviços"]) == "Plataforma de Serviços"
    assert find_sensitive_term("circuit breaker gateway", ["GW-7"]) is None


async def test_queries_with_sensitive_terms_never_reach_the_provider():
    provider = FakeProvider({})
    agent, _ = make_agent(["GW-7 circuit breaker", "bulkhead pattern"], provider)
    result = await agent.run(make_profile())

    assert provider.queries == ["bulkhead pattern"]
    [blocked] = [entry for entry in result.log if entry.erro and "T6" in entry.erro]
    assert "GW-7" not in blocked.query


async def test_documents_after_reference_date_are_not_prior_art():
    provider = FakeProvider({"q": [hit("old", date(2020, 1, 1)), hit("new", date(2025, 6, 1)), hit("undated", None)]})
    agent, llm = make_agent(["q"], provider)
    result = await agent.run(make_profile())

    docs = {doc.id: doc for doc in result.fontes}
    assert docs["old"].anterior_a_referencia is True
    assert docs["new"].anterior_a_referencia is False
    assert docs["undated"].anterior_a_referencia is None and not docs["undated"].data_verificada
    assert docs["new"].comparacao is None  # posteriores não são comparados
    assert docs["old"].comparacao == COMPARISON
    [entry] = result.log
    assert entry.selecionados == ["old", "undated"]
    assert entry.descartados[0].alvo == "new" and "depois da data de referência" in entry.descartados[0].motivo
    assert entry.filtros["publicado_ate"] == "2025-01-06"


async def test_selection_interleaves_queries_dedupes_and_caps():
    provider = FakeProvider(
        {"a": [hit("a1", None), hit("shared", None), hit("a3", None)], "b": [hit("shared", None), hit("b2", None)]}
    )
    agent, _ = make_agent(["a", "b"], provider, max_docs=3)
    result = await agent.run(make_profile())

    assert [doc.id for doc in result.fontes] == ["a1", "shared", "b2"]
    reasons = [d.motivo for entry in result.log for d in entry.descartados]
    assert "duplicado de outra query" in reasons
    assert any("limite de 3" in reason for reason in reasons)


async def test_failed_search_is_logged_and_does_not_stop_the_front():
    class BrokenProvider(FakeProvider):
        async def search(self, query, before, limit):
            raise TimeoutError("boom")

    agent, _ = make_agent(["q"], BrokenProvider({}))
    result = await agent.run(make_profile())
    assert result.fontes == []
    assert result.log[0].erro == "TimeoutError: boom"
