import json

import pytest

from backend.checks import diverg, falhas, pergunta, recalc
from backend.checks.data import prose_number
from backend.checks.runner import CHECKS, check_fragments, run_checks, with_check_fragments
from backend.criteria.citation import quote_in
from backend.extraction.schema import CanonicalProject, Fragment, ProjectContext
from tests.factories import synthetic_canonical


def row(file_type, fid, **data):
    return Fragment(id=fid, alias=f"evidencias/x.csv#{fid}", file="evidencias/x.csv", file_type=file_type, anchor=fid,
                    text=";".join(f"{v}" for v in data.values()), nature="registro_primario",
                    data={k: (None if v is None else str(v)) for k, v in data.items()})


def doc(file_type, anchor, text, nature="sintese"):
    return Fragment(id=f"PRJ90-{file_type}#{anchor}", alias=f"{file_type}#{anchor}", file=file_type,
                    file_type=file_type, anchor=anchor, text=text, nature=nature)


def project(*fragments):
    return CanonicalProject(project_code="PRJ90", files=[], fragments=list(fragments), context=ProjectContext())


def result(trial, version, metric, op, value, base, rate=None, nature="desempenho"):
    return row("resultados", trial, ensaio_id=trial, versao=version, metrica=metric, operacao=op, valor=value,
               base_de_calculo=base, taxa_percentual=rate, natureza=nature)


def measure(rid, trial, version, numerador=None, denominador=None, valor=None, peso=None):
    return row("medicoes", rid, registro_id=rid, ensaio_id=trial, versao=version, valor=valor, numerador=numerador,
               denominador=denominador, peso=peso)


async def test_every_check_runs_on_the_synthetic_package_without_tokens():
    report = run_checks(await synthetic_canonical())
    assert set(report.results) == set(CHECKS)
    assert all(r.status != "falhou" for r in report.results.values()), report.results
    assert report.results["CHK-RECALC"].status == "ok"
    assert report.results["CHK-VERSOES"].facts["versoes_sem_ensaio"] == ["prioridade-v1"]
    assert report.results["CHK-VERSOES"].facts["parametros_nulos"] == ["parametros.limiar_desempate"]
    assert report.results["CHK-TEMPO"].facts["documento_inicial_antes_dos_ensaios"] is True
    # "acertou todos os 200 lotes" × 196/200 recorded: a totality claim the record contradicts
    [candidate] = report.results["CHK-DIVERG"].facts["divergencias"]
    assert candidate["tipo"] == "totalidade" and candidate["registro_fragmento"] == "PRJ90-S02"


def test_count_sums_only_within_the_same_trial_and_empty_is_never_zero():
    canonical = project(
        measure("M1", "S01", "v1", 8, 12), measure("M2", "S01", "v1", 2, 3), measure("M3", "S02", "v2", 12, 12),
        result("S01", "v1", "acertos", "contagem", 10, 15), result("S02", "v2", "acertos", "contagem", 11, 12),
        measure("M4", "S03", "v2"), result("S03", "v2", "acertos", "contagem", 5, 5))
    facts = recalc.check(canonical).facts
    situation = {line["ensaio_id"]: line["situacao"] for line in facts["linhas"]}
    assert situation == {"S01": "batendo", "S02": "nao_batendo", "S03": "vazio"}
    assert facts["nao_batendo"] == ["S02"]


def test_percentile_95_by_position_with_weights():
    rows = [measure(f"M{i}", "S01", "v1", valor=v, peso=w) for i, (v, w) in enumerate([(10, 90), (50, 5), (90, 5)])]
    assert recalc.recompute("percentil_95", rows) == (50.0, 100.0)
    assert recalc.recompute("mediana", [measure("A", "S", "v", valor=3), measure("B", "S", "v", valor=9)])[0] == 6


def test_failures_follow_the_direction_of_the_metric():
    canonical = project(row("cronologia", "CR1", data="2025-01-01", versao="a-v1"),
                        row("cronologia", "CR2", data="2025-02-01", versao="b-v2"),
                        result("S1", "a-v1", "falsos alertas", "media", "7.8", None, "7.8"),
                        result("S2", "b-v2", "falsos alertas", "media", "5.5", None, "5.5"))
    facts = falhas.check(canonical).facts
    assert facts["direcao"]["falsos alertas"] == "menor_e_melhor" and facts["pioras"] == []


@pytest.mark.parametrize("said, expected", [("Registramos 400 casos corretos.", 1),
                                            ("Registramos 4000 casos corretos.", 0)])
def test_close_but_different_number_is_a_divergence_candidate(said, expected):
    canonical = project(result("S1", "x-v1", "casos corretos", "contagem", 412, 500, "82.4"),
                        doc("entrevista", "conclusao", said, "depoimento"))
    assert len(diverg.find(canonical)) == expected


def test_fraction_in_words_and_absence_claims():
    canonical = project(result("S5", "etapas-v3", "replays aceitos", "contagem", 0, 20, "0.0"),
                        result("S2", "banco-v1", "trocas com leitura indevida", "contagem", 2, 8, "25.0"),
                        doc("entrevista", "conclusao", "A versão em etapas aceitou um dos vinte replays.", "depoimento"),
                        doc("entrevista", "ocorrencia", "Não registramos nenhuma leitura indevida.", "depoimento"))
    kinds = sorted(c["tipo"] for c in diverg.find(canonical))
    assert kinds == ["ausencia_de_falha", "numero_diferente"]


def test_prose_numbers_use_the_portuguese_separators():
    assert prose_number("1.152") == 1152 and prose_number("2,8") == 2.8


@pytest.mark.parametrize("question, flagged", [
    ("Como aplicar idempotência conhecida ao reenvio?", True),
    ("Como integrar ao cofre contratado?", True),
    ("Como usar o recurso disponível no produto?", True),
    ("É possível associar sem depender de igualdade exata?", False)])
def test_registered_question_that_names_the_known_solution(question, flagged):
    activities = [row("atividades", f"A{i}", id_atividade=f"A{i}", resultado_ou_saida=f"Pergunta: {question}")
                  for i in range(2)]  # the same activity in the CSV and the XLSX: one question
    result = pergunta.check(project(*activities))
    assert len(result.facts["perguntas"]) == 1 and result.facts["aplica_solucao_conhecida"] is flagged


async def test_file_types_come_from_the_content_not_the_name():
    canonical = await synthetic_canonical()
    renamed = canonical.model_copy(update={"fragments": [
        f.model_copy(update={"file": "x.csv", "alias": f.alias.replace("resultados.csv", "x.csv")})
        for f in canonical.fragments]})
    assert run_checks(renamed).results["CHK-RECALC"].facts == run_checks(canonical).results["CHK-RECALC"].facts


async def test_a_check_is_a_citable_derived_fragment():
    canonical = await synthetic_canonical()
    report = run_checks(canonical)
    fragments = {f.anchor: f for f in check_fragments(canonical, report)}
    recalc_fragment = fragments["CHK-RECALC"]
    assert recalc_fragment.nature == "derivado" and recalc_fragment.file_type == "checagem"
    assert json.loads(recalc_fragment.text)["id"] == "CHK-RECALC"
    assert quote_in('"situacao": "batendo"', recalc_fragment.text)
    assert not quote_in('"situacao": "inventada"', recalc_fragment.text)
    assert with_check_fragments(canonical, report).fragment("PRJ90-CHK-RECALC") is not None


def test_a_broken_check_fails_alone(monkeypatch):
    from backend.checks import runner

    monkeypatch.setitem(runner.CHECKS, "CHK-TEMPO", lambda c: 1 / 0)
    report = run_checks(project())
    assert report.results["CHK-TEMPO"].status == "falhou"
    assert report.results["CHK-RECALC"].status == "nao_aplicavel"


def test_inc_d2_support_on_a_known_solution_question_counts_against():
    from backend.catalog.loader import get_catalog
    from backend.criteria.schemas import CriterionResult
    from backend.graph.consistency import apply_consistency
    from backend.graph.scoring import score_rule
    from tests.factories import evidence, run

    activities = [row("atividades", "PRJ90-ATV01", id_atividade="PRJ90-ATV01",
                      resultado_ou_saida="Pergunta: Como aplicar idempotência conhecida ao reenvio?")]
    report = run_checks(project(*activities))
    support = evidence("INC-D2", source="PRJ90-ATV01", quote="Como aplicar idempotência conhecida ao reenvio?")
    results = {"INC": CriterionResult(criterion="INC", rules=[run("INC-D2", support)])}
    consistency = apply_consistency(results, get_catalog(), checks=report, neutralize=False, inc_d2=True)
    assert [i.evidence_id for i in consistency.inverted] == [support.id]
    assert support.polarity == "positiva" and support.scored_polarity == "negativa"
    assert score_rule(results["INC"].rule("INC-D2"), get_catalog().get("INC-D2")).score == 0


def test_kept_parameter_claim_against_a_recorded_change():
    config = Fragment(id="PRJ90-EV05#parametros", alias="evidencias/configuracao.json#parametros",
                      file="evidencias/configuracao.json", file_type="configuracao", anchor="parametros",
                      text='{"limiar_inicial": 3, "limiar_final": 5, "janela": 10}', nature="registro_primario")
    canonical = project(config, doc("entrevista", "conclusao", "Mantivemos o limiar inicial do serviço S2.",
                                    "depoimento"))
    [candidate] = diverg.find(canonical)
    assert candidate["tipo"] == "parametro_mantido" and candidate["registrado"] == "limiar: 3 → 5"
    unchanged = project(config.model_copy(update={"text": '{"limiar_inicial": 5, "limiar_final": 5}'}),
                        doc("entrevista", "conclusao", "Mantivemos o limiar inicial.", "depoimento"))
    assert diverg.find(unchanged) == []


def test_a_divergence_the_sub_agent_already_wrote_is_not_repeated():
    from backend.checks.divergences import add_check_divergences
    from backend.checks.models import CheckResult, ChecksReport
    from backend.criteria.schemas import CriterionResult, Divergence

    written = Divergence(criterion="SIS", testimony_fragment_id="E#conclusao", testimony_quote="Reduziu para 2,1 pontos",
                         record_fragment_id="R#x", record_alias="resultados.csv#x", record_quote="3.7", statement="s")
    candidate = {"depoimento_fragmento": "E#conclusao", "depoimento_trecho": "Reduziu para 2,1 pontos.",
                 "registro_fragmento": "PRJ-S02", "registro_alias": "a", "registro_trecho": "b", "frase": "f"}
    checks = ChecksReport(results={"CHK-DIVERG": CheckResult(id="CHK-DIVERG", status="alerta",
                                                             facts={"divergencias": [candidate]})})
    results = {"SIS": CriterionResult(criterion="SIS", divergences=[written])}
    assert add_check_divergences(results, project(), checks) == 0
