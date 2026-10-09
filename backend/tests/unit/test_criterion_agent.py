import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.agent import CriteriaRunner
from backend.criteria.doc_sub import DocSubOut
from backend.criteria.web_sub import QueryPlanOut, WebJudgeOut
from tests.factories import synthetic_canonical
from tests.fakes import FakeLLM, FakeSearchProvider, user_text


def empty_doc(_):
    return DocSubOut(evidencias=[], regras_sem_evidencia=[], divergencias=[], elos_ausentes=[])


def judge(messages):
    closest = {"fonte_id": "src-a", "cobertura": "parcial", "o_que_o_projeto_tem_a_mais": "desempate"}
    return WebJudgeOut(evidencias=[], regras_sem_evidencia=[], documento_mais_proximo=closest)


@pytest.fixture
async def canonical():
    return await synthetic_canonical()


async def test_runs_five_criteria_in_order_and_passes_closest_doc(canonical):
    from backend.search.base import SearchHit

    hit = SearchHit(id="src-a", provider="openalex", title="Closest paper", url="https://doi.org/a", snippet="s")
    providers = {"literatura": FakeSearchProvider("openalex", [hit])}
    llm = FakeLLM({DocSubOut: empty_doc, WebJudgeOut: judge,
                   QueryPlanOut: QueryPlanOut(queries=[{"frente": "literatura", "query": "dependency queue batch", "regras": []}])})
    stages = []
    runner = CriteriaRunner(llm, get_catalog(), providers, on_stage=lambda name, status, error=None: stages.append((name, status)))
    results = await runner.run_all(canonical)

    assert list(results) == ["NOV", "CRI", "INC", "SIS", "REP"]
    assert ("NOV", "concluida") in stages and ("INC", "concluida") in stages
    judge_calls = llm.calls_for(WebJudgeOut)
    assert len(judge_calls) == 3  # NOV, CRI, INC have web rules; SIS and REP do not
    assert any("Closest paper" in user_text(call) for call in judge_calls[1:])
    sis_rules = {r.rule_id: r.status for r in results["SIS"].rules}
    assert sis_rules["SIS-D4"] == "na"
    assert sis_rules["SIS-D3"] == "parcial"
    assert len(results["NOV"].rules) == 18


async def test_one_criterion_failing_does_not_stop_the_others(canonical):
    def doc(messages):
        if "Sistematicidade" in user_text(messages):
            raise RuntimeError("boom")
        return empty_doc(messages)

    llm = FakeLLM({DocSubOut: doc, WebJudgeOut: judge, QueryPlanOut: QueryPlanOut(queries=[])})
    results = await CriteriaRunner(llm, get_catalog(), {}).run_all(canonical)
    assert all(r.status in ("nao_executada", "na", "parcial") for r in results["SIS"].rules)
    assert results["REP"].errors == []
