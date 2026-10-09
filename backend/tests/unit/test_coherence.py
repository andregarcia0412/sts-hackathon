from backend.catalog.loader import get_catalog
from backend.criteria.schemas import CriterionResult
from backend.graph.classify import classify
from backend.graph.coherence import CONFLICT_NOTE, check_coherence
from backend.graph.options import JudgeOptions
from backend.graph.states import CriterionState, StateJudgeOut, judge_state
from tests.factories import ELIGIBLE_STATES, evidence, run
from tests.fakes import FakeLLM, user_text

REASK = JudgeOptions(coherence_mode="reask")


def answers(*states):
    """The judge answers these states in order (the last one repeats)."""
    queue = list(states)

    def handler(messages):
        state = queue.pop(0) if len(queue) > 1 else queue[0]
        return StateJudgeOut(estado=state, justificativa="porque sim")

    return handler


def nov_result(config_negative=False):
    rules = [run("NOV-D2", evidence("NOV-D2", source="PRJ90-EV06#1")),
             run("NOV-D6", evidence("NOV-D6", source="PRJ90-S02", nature="registro_primario"))]
    if config_negative:
        rules.append(run("NOV-D10", evidence("NOV-D10", "negativa", source="PRJ90-EV06#1")))
    return CriterionResult(criterion="NOV", rules=rules)


def sis_result():
    return CriterionResult(criterion="SIS", rules=[run("SIS-D12", evidence("SIS-D12", source="PRJ90-S02",
                                                                           nature="registro_primario"))])


def check(criterion, state, column, score, n_rules=9, llm_column=None, gate_conflicts=()):
    return check_coherence(criterion, state, column, llm_column or column, list(gate_conflicts), score, n_rules,
                           get_catalog(), REASK)


def test_strong_positive_score_contradicts_the_insufficient_column():
    contradiction = check("NOV", "INDETERMINADA", "insuficiente", 89)
    assert contradiction.source == "juiz" and contradiction.strength == "forte_positivo"
    assert contradiction.choices == ["DEMONSTRADA NO RECORTE", "NÃO DEMONSTRADA"]


def test_sis_partial_with_strong_score_asks_experiment_or_acceptance_never_rd():
    contradiction = check("SIS", "PARCIAL", "insuficiente", 90)
    assert contradiction.choices == ["DOCUMENTADA", "DOCUMENTADA COMO ACEITE"]
    assert check("SIS", "DOCUMENTADA COMO ACEITE", "rotina", 100) is None  # well documented acceptance is coherent


def test_strong_negative_does_not_contradict_insufficient_but_contradicts_rd():
    assert check("NOV", "INDETERMINADA", "insuficiente", 17) is None  # lack of proof is not proof against
    contradiction = check("NOV", "DEMONSTRADA NO RECORTE", "pd", 20)
    assert contradiction.choices == ["NÃO DEMONSTRADA", "INDETERMINADA"]


def test_weak_or_thin_scores_are_never_strong():
    assert check("NOV", "INDETERMINADA", "insuficiente", 64) is None
    assert check("NOV", "INDETERMINADA", "insuficiente", 95, n_rules=3) is None
    assert check("NOV", "INDETERMINADA", "insuficiente", None) is None


def test_numeric_record_gate_is_not_a_contradiction_of_the_judge():
    assert check("INC", "ALEGADA, NÃO VERIFICÁVEL", "insuficiente", 90, llm_column="pd") is None


async def test_reask_resolves_when_the_judge_changes_and_records_the_original_state():
    llm = FakeLLM({StateJudgeOut: answers("INDETERMINADA", "DEMONSTRADA NO RECORTE")})
    state = await judge_state(llm, get_catalog(), nov_result(), True, score=89, n_rules=9, options=REASK)
    assert state.state == "DEMONSTRADA NO RECORTE"
    assert state.coherence.status == "resolvida" and state.coherence.rejudged
    assert state.coherence.original_state == "INDETERMINADA" and state.coherence.original_source == "juiz"
    calls = llm.calls_for(StateJudgeOut)
    assert len(calls) == 2
    second = user_text(calls[1])
    assert "<contradicao>" in second and "89" in second and "DEMONSTRADA NO RECORTE | NÃO DEMONSTRADA" in second
    assert "<contradicao>" not in user_text(calls[0])


async def test_reask_that_insists_keeps_the_judge_state_and_flags_the_class():
    llm = FakeLLM({StateJudgeOut: answers("INDETERMINADA")})
    state = await judge_state(llm, get_catalog(), nov_result(), True, score=89, n_rules=9, options=REASK)
    assert state.state == "INDETERMINADA"  # the code never picks the state from the score
    assert state.coherence.status == "incoerente" and CONFLICT_NOTE in state.gates
    assert len(llm.calls_for(StateJudgeOut)) == 2  # at most one new judgement

    states = {c: CriterionState.of(c, s) for c, s in ELIGIBLE_STATES.items()} | {"NOV": state}
    suggestion = classify(states)
    assert suggestion.inconsistent and "NOV" in suggestion.path[-1]


async def test_configuration_gate_does_not_force_against_a_strong_score_and_judges_again():
    llm = FakeLLM({StateJudgeOut: answers("DEMONSTRADA NO RECORTE")})
    state = await judge_state(llm, get_catalog(), nov_result(config_negative=True), True, score=75, n_rules=8,
                              options=REASK)
    assert state.state == "DEMONSTRADA NO RECORTE"
    assert any("NOV-D10 em conflito com score 75" in gate for gate in state.gates)
    assert state.coherence.original_source == "gate" and state.coherence.status == "resolvida"
    assert "NOV-D10" in user_text(llm.calls_for(StateJudgeOut)[1])


async def test_configuration_gate_still_forces_below_the_threshold():
    llm = FakeLLM({StateJudgeOut: answers("DEMONSTRADA NO RECORTE")})
    state = await judge_state(llm, get_catalog(), nov_result(config_negative=True), True, score=64, n_rules=8,
                              options=REASK)
    assert state.state == "NÃO DEMONSTRADA" and state.coherence is None
    assert len(llm.calls_for(StateJudgeOut)) == 1


async def test_off_and_flag_never_ask_again():
    for mode, expected in (("off", None), ("flag", "incoerente")):
        llm = FakeLLM({StateJudgeOut: answers("PARCIAL")})
        state = await judge_state(llm, get_catalog(), sis_result(), True, score=90, n_rules=5,
                                  options=JudgeOptions(coherence_mode=mode))
        assert state.state == "PARCIAL" and len(llm.calls_for(StateJudgeOut)) == 1
        assert (state.coherence.status if state.coherence else None) == expected


async def test_force_adopts_the_score_column_only_in_the_core_criteria():
    force = JudgeOptions(coherence_mode="force")
    state = await judge_state(FakeLLM({StateJudgeOut: answers("INDETERMINADA")}), get_catalog(), nov_result(), True,
                              score=89, n_rules=9, options=force)
    assert state.state == "DEMONSTRADA NO RECORTE" and state.coherence.status == "resolvida"
    sis = await judge_state(FakeLLM({StateJudgeOut: answers("PARCIAL")}), get_catalog(), sis_result(), True,
                            score=90, n_rules=5, options=force)
    assert sis.state == "PARCIAL" and sis.coherence.status == "incoerente"


def test_benchmark_counts_contradictions_and_column_changes_against_the_answer_key():
    from backend.benchmark.metrics import coherence
    from backend.benchmark.models import RunSnapshot
    from backend.benchmark.reference import ExpectedCase
    from backend.graph.coherence import Coherence

    record = Coherence(score=89, rules_with_evidence=9, strength="forte_positivo", original_state="INDETERMINADA",
                       original_source="juiz", rejudged=True, status="resolvida")
    runs = [RunSnapshot(set="historico", code="PRJ90", repeat=1, analysis_id="a", status="concluida",
                        states={"NOV": "DEMONSTRADA NO RECORTE", "SIS": "PARCIAL"},
                        coherence={"NOV": record, "SIS": record.model_copy(update={
                            "original_state": "PARCIAL", "status": "incoerente"})})]
    expected = {"PRJ90": ExpectedCase(code="PRJ90", source="oficial", expected_class="eligible",
                                      states={"NOV": "DEMONSTRADA NO RECORTE", "SIS": "DOCUMENTADA"})}
    metrics = coherence(runs, expected, get_catalog())
    assert metrics.contradictions == {"NOV": 1, "SIS": 1} and metrics.by_source == {"juiz": 2}
    assert (metrics.rejudged, metrics.resolved, metrics.incoherent) == (2, 1, 1)
    assert (metrics.changed_column, metrics.changed_column_hits, metrics.changed_column_misses) == (1, 1, 0)


def test_routine_chosen_by_the_judge_against_a_strong_positive_score_is_a_contradiction():
    contradiction = check("CRI", "NÃO DEMONSTRADA", "rotina", 89)
    assert contradiction.source == "juiz" and contradiction.choices == ["DEMONSTRADA NO RECORTE", "NÃO DEMONSTRADA"]
    assert check("CRI", "NÃO DEMONSTRADA", "rotina", 64) is None  # weak score: the judge's call stands
    forced = check_coherence("CRI", "NÃO DEMONSTRADA", "rotina", "rotina", [], 89, 9, get_catalog(), REASK,
                             forced_by_gate=True)
    assert forced is None  # a gate forcing routine is not the judge's caution
    assert check("SIS", "DOCUMENTADA COMO ACEITE", "rotina", 100) is None  # acceptance well documented: coherent


async def test_routine_against_the_score_is_asked_again_with_the_burden_on_routine():
    cri = CriterionResult(criterion="CRI", rules=[run("CRI-D1", evidence("CRI-D1", source="PRJ90-EV06#2"))])
    llm = FakeLLM({StateJudgeOut: answers("NÃO DEMONSTRADA", "DEMONSTRADA NO RECORTE")})
    state = await judge_state(llm, get_catalog(), cri, True, score=88, n_rules=8, options=REASK)
    assert state.state == "DEMONSTRADA NO RECORTE" and state.coherence.status == "resolvida"
    block = user_text(llm.calls_for(StateJudgeOut)[1])
    assert "evidência de rotina" in block and "Falta de um registro não é prova de rotina" in block
