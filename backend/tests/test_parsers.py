"""Testes dos parsers sobre os arquivos REAIS do PRJ01.

Contratos (spec seção 5.1 e 8):
- âncora estável por fragmento;
- célula vazia → null, nunca 0 (vazio ≠ zero);
- XLSX com cabeçalho na linha 5;
- seções do metodo.md por §;
- PDF por página;
- natureza do fragmento (depoimento para a transcrição).
"""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
PRJ01 = BACKEND / "data" / "casos_test" / "PRJ01"


@pytest.fixture(scope="module")
def parsed():
    from ai_microservice.extraction.parsers import parse_project

    return parse_project(PRJ01)


def test_manifest_com_hash_por_arquivo(parsed):
    manifest = parsed["manifest"]
    files = {m["path"]: m for m in manifest["files"]}
    assert "evidencias/medicoes.csv" in files
    for path, m in files.items():
        assert m["sha256"], f"{path} sem hash"
        assert m["bytes"] > 0
    # pacote imutável: 14 artefatos (inventário declara 14 evidências)
    assert len(files) >= 14


def test_fragmentos_com_ancora_estavel(parsed):
    frags = parsed["fragments"]
    assert len(frags) > 50
    anchors = {f.anchor for f in frags}
    # âncoras esperadas do pacote uniforme
    assert "evidencias/metodo.md#2" in anchors
    assert "evidencias/medicoes.csv#PRJ01-S01" in anchors
    assert "dossie_projeto.pdf#p1" in anchors
    assert "transcricao_entrevista_tecnica.pdf#p1" in anchors
    # âncoras únicas
    assert len(anchors) == len(frags), "âncoras duplicadas"


def test_celula_vazia_e_null_nunca_zero(parsed):
    """medicoes.csv do PRJ01: coluna valor vazia nas linhas contador → None, nunca 0."""
    by_anchor = {f.anchor: f for f in parsed["fragments"]}
    frag = by_anchor["evidencias/medicoes.csv#PRJ01-S01"]
    row = frag.data
    assert row["valor"] is None, "célula vazia virou 0/string — vazio ≠ zero"
    assert row["numerador"] == "8"
    assert row["denominador"] == "12"
    assert row["metrica"] == "duplicatas retidas"
    # id do fragmento estável: registro_id
    assert frag.data["registro_id"] == "PRJ01-S01-M001"


def test_csv_detecta_ponto_e_virgula_e_bom(parsed):
    frag = next(
        f for f in parsed["fragments"] if f.anchor == "evidencias/cronologia.csv#PRJ01-CR01"
    )
    assert frag.data["evento"] == "Registro do problema e das referências anteriores"
    assert frag.data["data"] == "2025-01-06"
    assert frag.data["versao"] == "documento-inicial"


def test_xlsx_cabecalho_na_linha5(parsed):
    frags = [f for f in parsed["fragments"] if f.anchor.startswith("atividades.xlsx#")]
    assert len(frags) == 8, f"esperado 8 atividades, achei {len(frags)}"
    first = next(f for f in frags if "ATV01" in str(f.data.values()))
    assert first.data["fase"] == "Caracterização do problema"
    assert first.data["resultado_ou_saida"].startswith("Pergunta: Como aplicar idempotência")


def test_md_por_secao(parsed):
    frags = {f.anchor: f for f in parsed["fragments"] if f.anchor.startswith("evidencias/metodo.md#")}
    assert set(frags) == {f"evidencias/metodo.md#{i}" for i in range(1, 8)}
    s2 = frags["evidencias/metodo.md#2"]
    assert "deduplicação" in s2.text
    assert "Nenhum algoritmo do barramento foi modificado" in s2.text


def test_pdf_por_pagina_e_natureza(parsed):
    dossie = [f for f in parsed["fragments"] if f.anchor.startswith("dossie_projeto.pdf#")]
    assert len(dossie) == 1  # 1 página
    assert dossie[0].nature == "sintese"
    transc = [f for f in parsed["fragments"] if f.anchor.startswith("transcricao_entrevista_tecnica.pdf#")]
    assert len(transc) == 1
    assert transc[0].nature == "depoimento", "transcrição precisa entrar como depoimento (T9)"


def test_json_inteiro(parsed):
    frag = next(f for f in parsed["fragments"] if f.anchor == "evidencias/configuracao.json")
    assert frag.data["projeto_id"] == "PRJ01"
    assert frag.data["parametros"]["retencao_inicial_s"] == 30
    assert "deduplicacao-v1" in frag.data["versoes_registradas"]


def test_inventario_compara_conteudo_esperado(parsed):
    """Identificação de tipo pelo conteúdo validada contra inventario_evidencias.csv (divergência = flag)."""
    assert parsed["flags"] == [], f"flags de divergência não esperadas no PRJ01: {parsed['flags']}"