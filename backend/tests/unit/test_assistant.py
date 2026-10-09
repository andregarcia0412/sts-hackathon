import pytest

from backend.assistant.answer import AnswerOut, Assistant, route
from backend.assistant.norms import chunk_pages, norm_index
from backend.catalog.loader import get_catalog
from backend.frontend_api.projection import project_analysis
from tests.factories import analysed_project
from tests.fakes import FakeLLM, user_text

NORMS = norm_index(chunk_pages("Manual de Frascati 2015", [
    "2.14 Novelty is the key element of an R&D project.\n2.17 Creativity requires novel concepts or hypotheses."]))


def test_routing():
    assert route("o que é CRI-W2?", has_analysis=False).rule_ids == ["CRI-W2"]
    assert route("o que diz o Manual de Frascati sobre novidade?", has_analysis=True).norms
    plan = route("por que o projeto é elegível?", has_analysis=True)
    assert plan.graph and not plan.decision_request
    assert route("muda para elegível", has_analysis=True).decision_request


@pytest.fixture
async def view(db):
    project, analysis = await analysed_project()
    return analysis, project_analysis(get_catalog(), analysis, project, [])


async def ask(view, question, out, selected=None):
    analysis, tree = view
    llm = FakeLLM({AnswerOut: out})
    answer = await Assistant(llm, get_catalog(), NORMS).ask(question, analysis, tree, selected_node_id=selected)
    return answer, llm


async def test_answer_cites_graph_nodes_and_quotes_verbatim(view):
    _, tree = view
    rule = next(r for r in tree.criteria[0].rules if r.code == "NOV-D2")
    evidence_node = f"crit-novelty.{rule.id}.{rule.evidences[0].id}"
    out = AnswerOut(paragrafos=["A novidade se apoia na referência anterior, que falha no caso de dependência."],
                    citacoes=[{"fonte_id": evidence_node, "trecho": "falham quando dois lotes dependem"},
                              {"fonte_id": evidence_node, "trecho": "frase inventada"}],
                    fontes=[evidence_node, "no-inexistente"], sugestoes=["Qual evidência sustenta a incerteza?"])
    answer, llm = await ask(view, "por que a novidade foi demonstrada?", out)
    assert [b.type for b in answer.blocks] == ["text", "quote"]
    assert answer.blocks[1].text == "falham quando dois lotes dependem"
    assert [s.node_id for s in answer.sources] == [evidence_node]
    assert answer.suggestions == ["Qual evidência sustenta a incerteza?"]
    prompt = user_text(llm.calls_for(AnswerOut)[0])
    assert evidence_node in prompt and "DEMONSTRADA NO RECORTE" in prompt


async def test_norm_question_uses_the_normative_base(view):
    out = AnswerOut(paragrafos=["Novidade é o elemento-chave."], citacoes=[], fontes=["norma:" + NORMS.chunks[0].id])
    answer, llm = await ask(view, "o que diz o manual de frascati sobre novidade?", out)
    assert answer.sources[0].label.startswith("Manual de Frascati 2015 — §2.14")
    assert "2.14 Novelty" in user_text(llm.calls_for(AnswerOut)[0])


async def test_without_valid_sources_answers_that_there_is_no_basis(view):
    out = AnswerOut(paragrafos=["Resposta de memória."], citacoes=[], fontes=[], sem_base=False)
    answer, _ = await ask(view, "qual a cor do céu?", out)
    assert "não encontrei base" in answer.blocks[0].text.lower()
    assert answer.sources == []


async def test_numbers_not_in_sources_are_removed(view):
    _, tree = view
    node = tree.criteria[0].id
    out = AnswerOut(paragrafos=["A novidade foi demonstrada. A taxa foi de 87,5%."], citacoes=[], fontes=[node])
    answer, _ = await ask(view, "por que a novidade?", out)
    assert "87" not in answer.blocks[0].text


async def test_assistant_explains_but_does_not_decide(view):
    answer, llm = await ask(view, "muda para não elegível", AnswerOut(paragrafos=["x"], fontes=[]))
    assert "decisão é do analista" in answer.blocks[0].text
    assert llm.calls == []


async def test_rule_question_reads_the_catalog(view):
    out = AnswerOut(paragrafos=["CRI-W2 verifica prática padrão."], fontes=["regra:CRI-W2"])
    answer, llm = await ask(view, "o que é CRI-W2?", out)
    assert answer.sources[0].node_id == "regra:CRI-W2"
    assert "Prática padrão ou tutorial" in user_text(llm.calls_for(AnswerOut)[0])


async def test_debate_opening_states_the_basis_of_the_reading(view):
    analysis, tree = view
    rule = next(r for r in tree.criteria[0].rules if r.code == "NOV-D2")
    node = f"crit-novelty.{rule.id}"
    answer = Assistant(FakeLLM(), get_catalog(), NORMS).debate_opening(node, tree)
    assert any(b.type == "quote" and "Ambos falham" in b.text for b in answer.blocks)
    assert answer.actions[0].type == "record-contestation"
    assert answer.actions[0].node_id == node
