import re
from pathlib import Path

import pytest
import yaml

from backend.catalog.loader import CatalogError, CATALOG_PATH, QUESTIONNAIRE_PATH, get_catalog, parse_catalog
from backend.criteria.schemas import ClosestDoc, CriterionResult
from backend.graph.judge import JudgeOptions, judge_and_classify
from backend.graph.questionnaire import QuestionnaireOut, decide, judge_by_questionnaire
from tests.factories import ELIGIBLE_ANSWERS, ELIGIBLE_STATES, evidence, fake_answers, run
from tests.fakes import FakeLLM, user_text

QUESTIONNAIRE = JudgeOptions(judge_mode="questionario")


def table(criterion):
    return get_catalog().questionnaire.decisao[criterion]


def state_for(criterion, **answers):
    return decide(answers, table(criterion))[1].estado


def test_decision_table_follows_the_tree_of_the_historical_cases():
    assert state_for("NOV", N1="sim", N2="sim", N3="sim") == "NÃO DEMONSTRADA"  # the reference already did it
    assert state_for("NOV", N1="nao", N2="sim", N3="sim") == "DEMONSTRADA NO RECORTE"
    assert state_for("NOV", N1="nao", N2="sem_registro", N3="sim") == "INDETERMINADA"
    assert state_for("NOV", N1="nao", N2="nao", N3="sim") == "NÃO DEMONSTRADA"
    assert state_for("CRI", C1="nao", C2="sim", C3="nao") == "INDETERMINADA"  # key parameter null
    assert state_for("INC", I1="nao", I2="operacional", I3="nao") == "NÃO CARACTERIZADA"
    assert state_for("INC", I1="nao", I2="experimental", I3="sim") == "INVESTIGADA"
    assert state_for("INC", I1="nao", I2="nenhuma") == "ALEGADA, NÃO VERIFICÁVEL"  # missing answer = no record
    assert state_for("SIS", S1="sim", S2="aceite") == "DOCUMENTADA COMO ACEITE"
    assert state_for("SIS", S1="sem_registro", S2="experimento") == "PARCIAL"
    assert state_for("REP", R1="sim", R2="configuracao", R3="sim") == "DOCUMENTADA PARA A CONFIGURAÇÃO"
    assert state_for("REP", R1="sim", R2="conhecimento", R3="sim") == "DOCUMENTADA COM LIMITE"
    assert state_for("REP", R1="sim", R2="conhecimento", R3="nao") == "DOCUMENTADA NO ESCOPO"


def test_the_table_is_catalog_data():
    raw = yaml.safe_load(Path(CATALOG_PATH).read_text(encoding="utf-8"))
    questionnaire = yaml.safe_load(Path(QUESTIONNAIRE_PATH).read_text(encoding="utf-8"))
    questionnaire["decisao"]["SIS"][2]["estado"] = "DOCUMENTADA"  # aceite → DOCUMENTADA, just to prove it
    catalog = parse_catalog(raw, questionnaire)
    assert decide({"S1": "sim", "S2": "aceite"}, catalog.questionnaire.decisao["SIS"])[1].estado == "DOCUMENTADA"
    questionnaire["decisao"]["SIS"][2]["estado"] = "INVENTADO"
    with pytest.raises(CatalogError):
        parse_catalog(raw, questionnaire)


def test_questions_never_cite_a_project_code():
    assert not re.search(r"PRJ\d+", Path(QUESTIONNAIRE_PATH).read_text(encoding="utf-8"))


def sis_result():
    primary = evidence("SIS-D12", source="PRJ90-S02", nature="registro_primario")
    acceptance = evidence("SIS-D5", "negativa", source="PRJ90-EV06#3")
    return CriterionResult(criterion="SIS", rules=[run("SIS-D12", primary), run("SIS-D5", acceptance)]), primary


async def test_answers_become_the_state_with_a_justification_built_from_them():
    result, primary = sis_result()
    llm = FakeLLM({QuestionnaireOut: fake_answers({"S2": "aceite"})})
    state = await judge_by_questionnaire(llm, get_catalog(), result, True, options=QUESTIONNAIRE)
    assert state.state == "DOCUMENTADA COMO ACEITE" and state.column == "rotina"
    assert [a.pergunta for a in state.answers] == ["S1", "S2"]
    assert state.decision_rule.startswith("SIS linha 3: S2 = aceite")
    assert state.justification.startswith("Sistematicidade: DOCUMENTADA COMO ACEITE. S2 = aceite")
    assert "SIS-D5" in state.justification
    assert set(state.decisive_evidence_ids) <= {e.id for r in result.rules for e in r.evidences}
    prompt = user_text(llm.calls_for(QuestionnaireOut)[0])
    assert "S2 [experimento | aceite | sem_registro]" in prompt and "roteiros com resultado esperado" in prompt


async def test_answer_without_evidence_gets_a_new_attempt_then_counts_as_no_record():
    result, _ = sis_result()
    llm = FakeLLM({QuestionnaireOut: QuestionnaireOut(respostas=[
        {"pergunta": "S1", "resposta": "sim", "evidencias": ["ev-inventada"]},
        {"pergunta": "S2", "resposta": "sem_registro"}])})
    state = await judge_by_questionnaire(llm, get_catalog(), result, True, options=QUESTIONNAIRE)
    assert len(llm.calls_for(QuestionnaireOut)) == 2  # one new attempt with the errors
    retry = llm.calls_for(QuestionnaireOut)[1][-1]["content"]
    assert "S1 = sim exige pelo menos 1 ID" in retry and "S2: sem_registro exige o_que_falta" in retry
    assert {a.pergunta: a.status for a in state.answers} == {"S1": "nao_fundamentada", "S2": "nao_fundamentada"}
    assert state.state == "PARCIAL"
    assert any("resposta sem evidência: revisar" in gate for gate in state.gates)


async def test_no_record_answers_become_the_missing_link():
    result, _ = sis_result()
    llm = FakeLLM({QuestionnaireOut: fake_answers({"S1": "sem_registro"})})
    state = await judge_by_questionnaire(llm, get_catalog(), result, True, options=QUESTIONNAIRE)
    assert state.state == "PARCIAL"
    assert "S1" in state.missing_link.elo_ausente and "registro da execução" in state.missing_link.elo_ausente


async def test_gates_lock_answers_instead_of_running_in_parallel():
    nov = CriterionResult(
        criterion="NOV",
        rules=[run("NOV-D10", evidence("NOV-D10", "negativa", source="PRJ90-EV06#1")),
               run("NOV-W3", evidence("NOV-W3", source="src-a", nature="web", origin="web"))],
        closest_doc=ClosestDoc(source_id="src-a", title="Manual", url="https://x", cobertura="total",
                               o_que_o_projeto_tem_a_mais="nada"))
    llm = FakeLLM({QuestionnaireOut: fake_answers()})
    state = await judge_by_questionnaire(llm, get_catalog(), nov, True, options=QUESTIONNAIRE)
    assert state.state == "NÃO DEMONSTRADA"
    n1 = state.answers[0]
    assert (n1.pergunta, n1.resposta, n1.origem) == ("N1", "sim", "gate")
    prompt = user_text(llm.calls_for(QuestionnaireOut)[0])
    assert "N1 = sim (gate do sistema)" in prompt and "\nN1 [" not in prompt  # not asked again


async def test_numeric_record_gate_turns_yes_into_no_record():
    result = CriterionResult(criterion="INC", rules=[run("INC-D12", evidence("INC-D12", nature="sintese"))])
    llm = FakeLLM({QuestionnaireOut: fake_answers()})
    state = await judge_by_questionnaire(llm, get_catalog(), result, True, options=QUESTIONNAIRE)
    assert state.state == "ALEGADA, NÃO VERIFICÁVEL" and state.llm_state == "INVESTIGADA"
    assert any("registro numérico" in gate for gate in state.gates)


async def test_caveat_is_required_when_r3_is_yes():
    result = CriterionResult(criterion="REP", rules=[run("REP-D9", evidence("REP-D9", source="PRJ90-S02",
                                                                            nature="derivado"))])
    state = await judge_by_questionnaire(FakeLLM({QuestionnaireOut: fake_answers({"R3": "sim"})}), get_catalog(),
                                         result, True, options=QUESTIONNAIRE)
    assert state.state == "DOCUMENTADA COM LIMITE" and state.caveat is not None
    assert not state.caveat.complete()  # the class will flag "Com ressalvas" as incomplete


async def test_coherence_redoes_only_the_conflicting_answer():
    rules = [run(r, evidence(r, source=f"PRJ90-S0{i}", nature="registro_primario"))
             for i, r in enumerate(("NOV-D1", "NOV-D2", "NOV-D6", "NOV-D12"))]
    result = CriterionResult(criterion="NOV", rules=rules)
    calls = []

    def handler(messages):
        calls.append(messages)
        answers = {"N2": "sem_registro"} if len(calls) == 1 else {}
        return fake_answers(answers)(messages)

    options = JudgeOptions(judge_mode="questionario", coherence_mode="reask")
    state = await judge_by_questionnaire(FakeLLM({QuestionnaireOut: handler}), get_catalog(), result, True,
                                         score=90, n_rules=4, options=options)
    assert state.coherence.original_state == "INDETERMINADA" and state.coherence.status == "resolvida"
    assert state.state == "DEMONSTRADA NO RECORTE"
    second = calls[1][1]["content"]
    assert "Refaça: N2" in second and "N1 = nao (já respondida)" in second
    assert re.findall(r"^([A-Z]\d) \[", second.split("<perguntas>")[1].split("</perguntas>")[0], re.M) == ["N2"]


async def test_full_conclusion_in_questionnaire_mode(db):
    from tests.factories import analysed_project

    _, analysis = await analysed_project()
    llm = FakeLLM({QuestionnaireOut: fake_answers()})
    outcome = await judge_and_classify(llm, get_catalog(), analysis.criteria, QUESTIONNAIRE)
    assert {c: s.state for c, s in outcome.states.items()} == ELIGIBLE_STATES
    assert outcome.suggestion.suggested_class == "eligible"
    assert len(llm.calls_for(QuestionnaireOut)) == 5 and set(ELIGIBLE_ANSWERS) >= {
        a.pergunta for s in outcome.states.values() for a in s.answers}


async def test_answers_reach_the_graph_and_the_report(db):
    from backend.graph.builder import build_graph
    from backend.graph.judge import judge_and_classify
    from backend.report.builder import build_parecer
    from backend.report.pdf import render_pdf
    from tests.factories import analysed_project, synthetic_canonical

    _, analysis = await analysed_project()
    outcome = await judge_and_classify(FakeLLM({QuestionnaireOut: fake_answers()}), get_catalog(),
                                       analysis.criteria, QUESTIONNAIRE)
    analysis.states, analysis.suggestion = outcome.states, outcome.suggestion
    nodes, edges = build_graph("a1", await synthetic_canonical(), get_catalog(), analysis.criteria, outcome.scores,
                               outcome.states, outcome.suggestion)
    answer = next(n for n in nodes if n.node_id == "answer:SIS:S2")
    assert answer.props["effective"] == "experimento"
    assert any(e.source == "answer:SIS:S2" and e.target == "criterion:SIS" for e in edges)

    parecer = build_parecer(get_catalog(), analysis, [])
    sis = next(s for s in parecer.criterios if s.chave == "SIS")
    assert [a.pergunta for a in sis.respostas] == ["S1", "S2"] and sis.regra_de_decisao.startswith("SIS linha 2")
    assert render_pdf(parecer).startswith(b"%PDF")


async def test_web_alone_never_answers_that_the_solution_was_already_available():
    web = evidence("INC-W1", "negativa", source="src-patent", nature="web", origin="web")
    result = CriterionResult(criterion="INC", rules=[run("INC-W1", web)])
    llm = FakeLLM({QuestionnaireOut: QuestionnaireOut(respostas=[
        {"pergunta": "I1", "resposta": "sim", "evidencias": [web.id]},
        {"pergunta": "I2", "resposta": "sem_registro", "o_que_falta": "x"},
        {"pergunta": "I3", "resposta": "sem_registro", "o_que_falta": "x"}])})
    state = await judge_by_questionnaire(llm, get_catalog(), result, True, options=QUESTIONNAIRE)
    assert "I1 = sim exige pelo menos 1 evidência do próprio pacote" in llm.calls_for(QuestionnaireOut)[1][-1]["content"]
    assert state.answers[0].status == "nao_fundamentada" and state.state == "ALEGADA, NÃO VERIFICÁVEL"
