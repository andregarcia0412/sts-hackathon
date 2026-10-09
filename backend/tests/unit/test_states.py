import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.schemas import ClosestDoc, CriterionResult
from backend.graph.states import StateJudgeOut, judge_state
from tests.factories import evidence, run
from tests.fakes import FakeLLM, user_text


def out(state, ids=(), **extra):
    return StateJudgeOut(estado=state, justificativa="porque sim", evidencias_decisivas=list(ids), **extra)


async def judge(result, state_out, numeric_anywhere=True):
    llm = FakeLLM({StateJudgeOut: state_out})
    return await judge_state(llm, get_catalog(), result, numeric_record_in_analysis=numeric_anywhere), llm


async def test_llm_state_in_vocabulary_is_kept_with_valid_evidence_ids():
    primary = evidence("INC-D12", source="PRJ90-S02", nature="derivado")
    result = CriterionResult(criterion="INC", rules=[run("INC-D12", primary)])
    state, llm = await judge(result, out("INVESTIGADA", [primary.id, "ev-inventada"]))
    assert state.state == "INVESTIGADA"
    assert state.column == "pd"
    assert state.decisive_evidence_ids == [primary.id]
    assert state.gates == []
    prompt = user_text(llm.calls_for(StateJudgeOut)[0])
    assert primary.id in prompt and "ALEGADA, NÃO VERIFICÁVEL" in prompt


async def test_state_outside_vocabulary_is_not_accepted():
    result = CriterionResult(criterion="NOV", rules=[run("NOV-D2", evidence("NOV-D2"))])
    state, _ = await judge(result, out("ÓTIMA"))
    assert state.state is None
    assert "vocabulário" in state.error


async def test_gate_full_coverage_document_forces_negative():
    closest = ClosestDoc(source_id="s", title="t", url="u", cobertura="total", o_que_o_projeto_tem_a_mais="")
    result = CriterionResult(criterion="NOV", rules=[run("NOV-D2", evidence("NOV-D2"))], closest_doc=closest)
    state, _ = await judge(result, out("DEMONSTRADA NO RECORTE"))
    assert state.state == "NÃO DEMONSTRADA"
    assert state.llm_state == "DEMONSTRADA NO RECORTE"
    assert any("NOV-W3" in g for g in state.gates)


@pytest.mark.parametrize("criterion,rule", [("NOV", "NOV-D4"), ("NOV", "NOV-D10"), ("CRI", "CRI-D5")])
async def test_gate_configuration_rules_force_negative(criterion, rule):
    negative = evidence(rule, "negativa", source="PRJ90-EV06#2")
    result = CriterionResult(criterion=criterion, rules=[run(rule, negative)])
    state, _ = await judge(result, out("INDETERMINADA"))
    assert state.state == "NÃO DEMONSTRADA"
    assert any(rule in g for g in state.gates)


async def test_gate_only_when_negative_dominates():
    result = CriterionResult(criterion="CRI", rules=[run("CRI-D5", evidence("CRI-D5", "negativa", source="a"),
                                                         evidence("CRI-D5", source="b"))])
    state, _ = await judge(result, out("DEMONSTRADA NO RECORTE"))
    assert state.state == "DEMONSTRADA NO RECORTE"


async def test_strong_state_without_numeric_record_is_downgraded():
    result = CriterionResult(criterion="SIS", rules=[run("SIS-D5", evidence("SIS-D5", source="PRJ90-EV06#3"))])
    state, _ = await judge(result, out("DOCUMENTADA"))
    assert state.state == "PARCIAL"
    assert any("registro numérico" in g for g in state.gates)


async def test_novelty_accepts_numeric_record_anywhere_in_the_analysis():
    result = CriterionResult(criterion="NOV", rules=[run("NOV-D2", evidence("NOV-D2"))])
    state, _ = await judge(result, out("DEMONSTRADA NO RECORTE"), numeric_anywhere=True)
    assert state.state == "DEMONSTRADA NO RECORTE"
    state, _ = await judge(result, out("DEMONSTRADA NO RECORTE"), numeric_anywhere=False)
    assert state.state == "INDETERMINADA"


async def test_reproduction_with_limit_carries_caveat():
    primary = evidence("REP-D9", source="PRJ90-S02", nature="derivado")
    result = CriterionResult(criterion="REP", rules=[run("REP-D9", primary)])
    state, _ = await judge(result, out("DOCUMENTADA COM LIMITE", [primary.id], recorte_sustentado="lotes até 500",
                                       limitacao="lotes maiores", evidencia_necessaria="ensaio com 1000"))
    assert state.column == "pd"
    assert state.caveat.limitacao == "lotes maiores"


async def test_llm_failure_leaves_state_not_executed():
    result = CriterionResult(criterion="NOV", rules=[])
    state, _ = await judge(result, RuntimeError("down"))
    assert state.state is None
    assert state.error
