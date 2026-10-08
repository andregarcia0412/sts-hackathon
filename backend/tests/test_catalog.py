"""Testes do catálogo de regras — validações da spec seção 4/8.

Roda de backend/: .venv/bin/python -m pytest tests/ -x -q
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

BACKEND = Path(__file__).resolve().parent.parent
CATALOG_PATH = BACKEND / "catalog" / "rules.yaml"
PRJ01 = BACKEND / "data" / "casos_test" / "PRJ01"


@pytest.fixture(scope="module")
def catalog() -> dict:
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_existe_e_versionado(catalog):
    assert catalog["catalog_version"] == "1.0.0"
    assert isinstance(catalog["rules"], list)


def test_contagem_da_auditoria(catalog):
    """Auditoria da spec: 66 ativas de critério (17 web + 49 documentais) — ativas incluem
    58 executáveis + 4 N/A + 4 parciais; + 9 absorvidas + 15 T + 7 CHK = 97."""
    rules = catalog["rules"]
    by_status = {}
    for r in rules:
        by_status.setdefault(r["status"], []).append(r)

    criterio = [r for r in rules if r["criterion"] not in ("transversal", "compartilhada")]
    ativas = [r for r in criterio if r["status"] != "absorvida"]
    assert len(ativas) == 66, f"esperado 66 ativas de critério, achei {len(ativas)}"
    web = [r for r in ativas if r["block"] == "web"]
    doc = [r for r in ativas if r["block"] == "documento"]
    assert len(web) == 17, f"esperado 17 web, achei {len(web)}"
    assert len(doc) == 49, f"esperado 49 documentais, achei {len(doc)}"
    # decomposição: 58 executáveis + 4 na + 4 parcial
    executaveis = [r for r in ativas if r["status"] == "aplicavel"]
    assert len(executaveis) == 58, f"esperado 58 executáveis, achei {len(executaveis)}"
    assert len([r for r in ativas if r["status"] == "na"]) == 4
    assert len([r for r in ativas if r["status"] == "parcial"]) == 4
    assert len(by_status.get("absorvida", [])) == 9
    assert len([r for r in rules if r["criterion"] == "transversal"]) == 15
    assert len([r for r in rules if r["criterion"] == "compartilhada"]) == 7


def test_sem_duplicado_ou_orfao(catalog):
    ids = [r["id"] for r in catalog["rules"]]
    assert len(ids) == len(set(ids)), "IDs duplicados no catálogo"
    # IDs esperados por critério, das notas
    esperados = {
        "NOV-W1", "NOV-W2", "NOV-W3", "NOV-W4", "NOV-W5", "NOV-W6", "NOV-W7", "NOV-W8",
        "NOV-D1", "NOV-D2", "NOV-D3", "NOV-D4", "NOV-D5", "NOV-D6", "NOV-D7", "NOV-D8",
        "NOV-D9", "NOV-D10", "NOV-D11", "NOV-D12",
        "CRI-W1", "CRI-W2", "CRI-W3", "CRI-W4", "CRI-W5",
        "CRI-D1", "CRI-D2", "CRI-D3", "CRI-D4", "CRI-D5", "CRI-D6", "CRI-D7", "CRI-D8",
        "CRI-D9", "CRI-D10",
        "INC-W1", "INC-W2", "INC-W3", "INC-W4",
        "INC-D1", "INC-D2", "INC-D3", "INC-D4", "INC-D5", "INC-D6", "INC-D7", "INC-D8",
        "INC-D9", "INC-D10", "INC-D11", "INC-D12", "INC-D13",
        "SIS-D1", "SIS-D2", "SIS-D3", "SIS-D4", "SIS-D5", "SIS-D6", "SIS-D7", "SIS-D8",
        "SIS-D9", "SIS-D10", "SIS-D11", "SIS-D12", "SIS-D13", "SIS-D14",
        "REP-D1", "REP-D2", "REP-D3", "REP-D4", "REP-D5", "REP-D6", "REP-D7", "REP-D8", "REP-D9",
        *[f"T{i}" for i in range(1, 16)],
        "CHK-TEMPO", "CHK-RECALC", "CHK-VERSOES", "CHK-FALHAS", "CHK-CONFIG", "CHK-ESCOPO", "CHK-DIVERG",
    }
    faltando = esperados - set(ids)
    sobrando = set(ids) - esperados
    assert not faltando, f"IDs das notas ausentes do catálogo: {faltando}"
    assert not sobrando, f"IDs no catálogo que não estão nas notas: {sobrando}"


def test_regras_llm_web_ativas_tem_prompt(catalog):
    for r in catalog["rules"]:
        if r["status"] != "aplicavel":
            continue
        modo = r["mode"]
        if ("llm" in modo or "web" in modo) and r["criterion"] not in ("transversal", "compartilhada"):
            assert r.get("prompt"), f"{r['id']} é {modo} e não tem prompt"


def test_status_reason_obrigatorio_quando_nao_aplicavel(catalog):
    for r in catalog["rules"]:
        if r["status"] in ("na", "parcial", "absorvida"):
            assert r.get("status_reason"), f"{r['id']} status={r['status']} sem status_reason"


def test_routing_aponta_artefatos_do_schema(catalog):
    """Todo artefato do routing existe no schema do pacote (14 artefatos)."""
    artifacts = {a["id"] for a in catalog["artifacts"]}
    # os 14 artefatos reais do PRJ01
    esperados = {
        "dossie_projeto.pdf", "registro_tecnico.pdf", "transcricao_entrevista_tecnica.pdf",
        "atividades.csv", "atividades.xlsx", "inventario_evidencias.csv",
        "evidencias/metodo.md", "evidencias/cronologia.csv", "evidencias/medicoes.csv",
        "evidencias/resultados.csv", "evidencias/configuracao.json",
        "evidencias/observacoes.csv", "evidencias/entradas.csv", "evidencias/revisao_tecnica.md",
    }
    assert artifacts == esperados, f"schema de artefatos diverge: {artifacts ^ esperados}"
    for r in catalog["rules"]:
        for rota in r.get("routing", []):
            base = rota.split("#")[0]
            assert base in artifacts, f"{r['id']} roteia para artefato inexistente: {rota}"


def test_secoes_do_metodo_validas(catalog):
    """routing com metodo.md#N referencia seções 1–7."""
    for r in catalog["rules"]:
        for rota in r.get("routing", []):
            if rota.startswith("evidencias/metodo.md#"):
                n = int(rota.split("#")[1])
                assert 1 <= n <= 7, f"{r['id']}: seção {n} fora do método (1–7)"


def test_chk_apontadas_existem(catalog):
    ids = {r["id"] for r in catalog["rules"]}
    for r in catalog["rules"]:
        if r.get("chk"):
            assert r["chk"] in ids, f"{r['id']} aponta chk inexistente {r['chk']}"


def test_loader_py_valida_o_catalogo(catalog):
    """O loader real (ai_microservice.catalog) carrega e valida — mesmo contrato destes testes."""
    from ai_microservice.catalog import load_catalog

    cat = load_catalog(CATALOG_PATH)
    assert cat.version == "1.0.0"
    por_id = {r.id: r for r in cat.rules}
    assert len(por_id) == 97
    assert por_id["NOV-D1"].criterion == "novidade"
    assert por_id["NOV-D8"].status.value == "na"
    assert por_id["NOV-D7"].absorbed_into == "T2"


def test_polarity_hint_valido(catalog):
    validos = {"positive", "negative", "informativa", "neutra"}
    for r in catalog["rules"]:
        assert r["polarity_hint"] in validos, f"{r['id']}: polarity_hint inválido {r['polarity_hint']}"


def test_scoring_role_valido(catalog):
    validos = {"mean", "informativa", "gate"}
    for r in catalog["rules"]:
        assert r["scoring_role"] in validos, f"{r['id']}: scoring_role inválido {r['scoring_role']}"