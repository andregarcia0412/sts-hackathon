import pytest

from backend.catalog.loader import get_catalog
from backend.criteria.doc_sub import DocSubOut, run_doc_sub
from tests.factories import synthetic_canonical
from tests.fakes import FakeLLM, user_text

GOOD_QUOTE = "Ambos falham quando dois lotes dependem do mesmo saldo."


def answer(**overrides):
    base = {
        "evidencias": [
            {"regra_id": "NOV-D2", "fragmento_id": "PRJ90-EV06#1", "quote": GOOD_QUOTE, "polaridade": "positiva",
             "justificativa": "Nomeia alternativas e onde falham."},
            {"regra_id": "NOV-D2", "fragmento_id": "PRJ90-EV06#1", "quote": GOOD_QUOTE, "polaridade": "positiva",
             "justificativa": "duplicada"},
            {"regra_id": "NOV-D1", "fragmento_id": "PRJ90-EV06#2", "quote": "texto que não existe", "polaridade": "positiva",
             "justificativa": "inventada"},
            {"regra_id": "NOV-D3", "fragmento_id": "PRJ90-EV10#mecanismo", "quote": "Criamos uma fila", "polaridade": "positiva",
             "justificativa": "da entrevista"},
            {"regra_id": "XYZ-1", "fragmento_id": "PRJ90-EV06#1", "quote": GOOD_QUOTE, "polaridade": "negativa",
             "justificativa": "regra não pedida"},
        ],
        "regras_sem_evidencia": [{"regra_id": "NOV-D5", "motivo": "nada sobre exclusões"}],
        "divergencias": [
            {"depoimento_fragmento_id": "PRJ90-EV10#conclusao", "depoimento_quote": "acertou todos os 200 lotes",
             "registro_fragmento_id": "PRJ90-S02", "registro_quote": "196;200", "afirmacao": "200/200", "registro_mostra": "196/200"},
            {"depoimento_fragmento_id": "PRJ90-S02", "depoimento_quote": "196;200",
             "registro_fragmento_id": "PRJ90-S01", "registro_quote": "150;200", "afirmacao": "x", "registro_mostra": "y"},
        ],
        "elos_ausentes": [{"descricao": "MEMO-90 sem versão", "evidencia_a_solicitar": "saída por versão",
                           "fragmento_ids": ["PRJ90-EV13#declaracao_da_equipe", "inventado#1"]}],
    }
    return base | overrides


@pytest.fixture
async def canonical():
    return await synthetic_canonical()


async def run(canonical, handler, criterion="NOV"):
    catalog = get_catalog()
    llm = FakeLLM({DocSubOut: handler})
    result = await run_doc_sub(llm, catalog, criterion, catalog.rules_for(criterion, "doc"), canonical, max_table_rows=50)
    return result, llm


async def test_valid_evidence_is_kept_with_source_and_nature(canonical):
    result, _ = await run(canonical, answer())
    runs = {r.rule_id: r for r in result.rules}
    [evidence] = runs["NOV-D2"].evidences  # duplicate (rule, fragment, quote) collapsed
    assert runs["NOV-D2"].status == "executada"
    assert evidence.source_id == "PRJ90-EV06#1"
    assert evidence.source_alias == "evidencias/metodo.md#1"
    assert evidence.nature == "sintese"
    assert evidence.origin == "doc"
    assert evidence.polarity == "positiva"
    assert evidence.id.startswith("ev-")


async def test_invented_quote_is_dropped_and_rule_has_no_evidence(canonical):
    result, _ = await run(canonical, answer())
    run_ = next(r for r in result.rules if r.rule_id == "NOV-D1")
    assert run_.status == "sem_evidencia"
    assert "gate" in run_.reason
    assert run_.dropped and "não encontrado literalmente" in run_.dropped[0]


async def test_testimony_never_becomes_evidence(canonical):
    result, _ = await run(canonical, answer())
    assert next(r for r in result.rules if r.rule_id == "NOV-D3").evidences == []


async def test_unrequested_rules_are_ignored_and_missing_rules_are_not_executed(canonical):
    result, _ = await run(canonical, answer())
    runs = {r.rule_id: r for r in result.rules}
    assert "XYZ-1" not in runs
    assert runs["NOV-D5"].status == "sem_evidencia"
    assert runs["NOV-D5"].reason == "nada sobre exclusões"
    assert runs["NOV-D12"].status == "nao_executada"


async def test_na_rules_skip_the_llm(canonical):
    result, llm = await run(canonical, answer())
    runs = {r.rule_id: r for r in result.rules}
    assert runs["NOV-D8"].status == "na"
    assert "patentes" in runs["NOV-D8"].reason
    assert "NOV-D8" not in user_text(llm.calls_for(DocSubOut)[0])


async def test_divergence_is_recorded_in_guide_format(canonical):
    result, _ = await run(canonical, answer())
    [divergence] = result.divergences
    assert divergence.testimony_fragment_id == "PRJ90-EV10#conclusao"
    assert divergence.record_alias == "evidencias/resultados.csv#PRJ90-S02"
    assert divergence.statement.startswith('A entrevista afirma "acertou todos os 200 lotes"')
    assert "prevalece o registro" in divergence.statement


async def test_missing_links_keep_only_real_fragment_ids(canonical):
    result, _ = await run(canonical, answer())
    [link] = result.missing_links
    assert link.fragment_ids == ["PRJ90-EV13#declaracao_da_equipe"]


async def test_positive_only_rule_drops_negative_evidence(canonical):
    handler = answer(evidencias=[{"regra_id": "CRI-D6", "fragmento_id": "PRJ90-EV06#2",
                                  "quote": "Ordenar lotes por grafo", "polaridade": "negativa", "justificativa": "x"}],
                     divergencias=[], elos_ausentes=[], regras_sem_evidencia=[])
    result, _ = await run(canonical, handler, criterion="CRI")
    assert next(r for r in result.rules if r.rule_id == "CRI-D6").evidences == []


async def test_llm_failure_marks_rules_not_executed_never_zero(canonical):
    result, _ = await run(canonical, RuntimeError("down"))
    statuses = {r.rule_id: r.status for r in result.rules}
    assert statuses["NOV-D1"] == "nao_executada"
    assert statuses["NOV-D8"] == "na"
    assert result.errors


async def test_prompt_wraps_data_and_carries_transversal_instructions(canonical):
    _, llm = await run(canonical, answer())
    messages = llm.calls_for(DocSubOut)[0]
    system = messages[0]["content"]
    user = user_text(messages)
    assert "DADO" in system and "T9:" in system and "T10:" in system
    assert "<fragmentos>" in user and "<depoimento>" in user
    assert "[PRJ90-EV06#2]" in user
    assert "NOV-D2" in user and "metodo.md §1" in user
