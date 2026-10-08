"""Testes das checagens compartilhadas (CHK-*) com valores conhecidos do PRJ01."""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
PRJ01 = BACKEND / "data" / "casos_test" / "PRJ01"


@pytest.fixture(scope="module")
def ctx():
    from ai_microservice.extraction.parsers import parse_project
    from ai_microservice.checks.runner import run_all_checks

    parsed = parse_project(PRJ01)
    return run_all_checks(parsed["fragments"])


def test_recalc_batendo(ctx):
    """PRJ01: S01 8/12, S02 12/12, S03 8/8, S04 40/40 — todas contagem, recalculáveis."""
    recalc = ctx["CHK-RECALC"]
    assert recalc["status"] == "ok"
    per_ensaio = {r["ensaio_id"]: r for r in recalc["rows"]}
    assert per_ensaio["PRJ01-S01"]["resultado"] == "batendo"
    assert per_ensaio["PRJ01-S01"]["valor_recalculado"] == 8
    assert per_ensaio["PRJ01-S01"]["base_recalculada"] == 12
    assert per_ensaio["PRJ01-S02"]["resultado"] == "batendo"
    assert per_ensaio["PRJ01-S04"]["valor_recalculado"] == 40
    assert all(r["resultado"] == "batendo" for r in recalc["rows"])


def test_recalc_vazio_nao_zero(ctx):
    """Célula vazia em resultados (ex.: taxa vazio) deve dar 'vazio', não 0."""
    recalc = ctx["CHK-RECALC"]
    assert recalc["status"] == "ok"
    # PRJ01: todas com taxa preenchida; a regra do vazio é testada via unidade da função
    from ai_microservice.checks.recalcula import compare_values

    assert compare_values(None, 5) == "vazio"
    assert compare_values(5, None) == "vazio"
    assert compare_values(None, None) == "vazio"
    assert compare_values(8, 8) == "batendo"
    assert compare_values(8, 9) == "nao_batendo"


def test_tempo_data_referencia_e_ordem(ctx):
    """PRJ01: 1º evento 2025-01-06 (documento-inicial) antes dos ensaios; datas progressivas."""
    tempo = ctx["CHK-TEMPO"]
    assert tempo["data_referencia"] == "2025-01-06"
    assert tempo["ordem_ok"] is True, "documento-inicial deve preceder os ensaios"
    assert tempo["progressivas_ok"] is True


def test_versoes_consistencia(ctx):
    """deduplicacao-v1/v2 em cronologia, medicoes e configuracao — sem parâmetro null."""
    versoes = ctx["CHK-VERSOES"]
    assert versoes["consistentes"] is True
    # versões de EXECUÇÃO (exclui documento-inicial/protocolo-r1/revisao-final)
    assert set(versoes["versoes_medicoes"]) == {"deduplicacao-v1", "deduplicacao-v2"}
    assert set(versoes["versoes_config"]) == {"deduplicacao-v1", "deduplicacao-v2"}
    assert versoes["parametros_nulos"] == []
    assert versoes["versoes_em_cronologia_sem_ensaio"] == []


def test_config_pre_pass(ctx):
    """PRJ01 é o caso clássico: manual BARR-2 datado antes fornece a função; ajuste dentro da faixa."""
    cfg = ctx["CHK-CONFIG"]
    assert cfg["referencia_anterior_tipo"] == "manual"
    assert cfg["ajuste_dentro_da_faixa"] is True
    assert cfg["funcao_ja_fornecida"] is True


def test_falhas_pre_pass(ctx):
    """PRJ01: v1 reteve 8/12 (falha experimental? não — não atingiu critério prévio) — classificação prévia."""
    falhas = ctx["CHK-FALHAS"]
    assert "deduplicacao-v1" in falhas["versoes_com_falha_ou_piora"]


def test_escopo_pre_pass(ctx):
    """Flags ..._executado: false no configuracao.json + §6."""
    esc = ctx["CHK-ESCOPO"]
    assert isinstance(esc["flags_executado_false"], list)


def test_diverg_pre_pass(ctx):
    """PRJ01: transcrição repete os números do registro (12 duplicatas) — sem divergência esperada."""
    dv = ctx["CHK-DIVERG"]
    assert isinstance(dv["divergencias"], list)
    assert len(dv["divergencias"]) == 0, "PRJ01 não deveria ter divergência depoimento × registro"