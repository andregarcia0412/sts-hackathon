"""Testes do grafo: schema, ID determinístico, versionamento e GraphStore."""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture()
def store(tmp_path):
    from ai_microservice.graph.store import JSONFileGraphStore

    return JSONFileGraphStore(base_dir=tmp_path / "graphs")


def test_id_deterministico():
    from ai_microservice.graph.builder import evidence_id

    a = evidence_id(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="Configurar deduplicação")
    b = evidence_id(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="Configurar deduplicação")
    c = evidence_id(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="Outra citação")
    assert a == b, "mesma entrada deve dar mesmo ID"
    assert a != c, "quote diferente deve dar ID diferente"


def test_upsert_idempotente(store, tmp_path):
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ01")
    ev = {
        "regra_id": "NOV-D1",
        "fonte": "evidencias/metodo.md#2",
        "quote": "Configurar deduplicação por (operação, versão).",
        "polaridade": "sustenta",
        "natureza": "sintese",
        "justificativa": "declara o mecanismo",
    }
    b.add_evidence(**ev)
    g1 = b.build()
    b.add_evidence(**ev)  # de novo — não deve duplicar nada
    g2 = b.build()
    assert len(g2.nodes) == len(g1.nodes), "upsert idempotente falhou: duplicou nó"
    assert len(g2.edges) == len(g1.edges), "upsert idempotente falhou: duplicou aresta"
    evs = [n for n in g2.nodes if n.type == "evidencia"]
    assert len(evs) == 1
    assert len([n for n in g2.nodes if n.type == "regra" and n.label == "NOV-D1"]) == 1
    # backbone: 1 projeto + 5 critérios sempre presentes
    assert len([n for n in g2.nodes if n.type == "projeto"]) == 1
    assert len([n for n in g2.nodes if n.type == "criterio"]) == 5


def test_versao_nunca_sobrescreve(store):
    from ai_microservice.graph.builder import GraphBuilder

    b1 = GraphBuilder(store=store, project_id="PRJ01")
    b1.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b1.save_version(catalog_version="1.0.0", model="gpt-oss:120b")
    b2 = GraphBuilder(store=store, project_id="PRJ01")
    b2.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b2.save_version(catalog_version="1.0.0", model="gpt-oss:120b")
    # v1 existe, v2 existe, v1 intocado
    base = store.base_dir / "PRJ01"
    v1 = base / "v1" / "nodes.json"
    v2 = base / "v2" / "nodes.json"
    assert v1.exists() and v2.exists()
    import json

    n1 = json.loads(v1.read_text())
    n2 = json.loads(v2.read_text())
    assert len(n1) == len(n2), "reexecução com mesma evidência não deve duplicar nós"
    # meta.json em ambas
    assert (base / "v1" / "meta.json").exists()
    assert (base / "v2" / "meta.json").exists()


def test_diff_versions(store):
    from ai_microservice.graph.builder import GraphBuilder

    b1 = GraphBuilder(store=store, project_id="PRJ01")
    b1.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b1.save_version(catalog_version="1.0.0", model="m")
    b2 = GraphBuilder(store=store, project_id="PRJ01")
    b2.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b2.add_evidence(regra_id="NOV-D2", fonte="evidencias/metodo.md#1", quote="q2", polaridade="contraria", natureza="sintese", justificativa="j2")
    b2.save_version(catalog_version="1.0.0", model="m")
    diff = store.diff_versions("PRJ01", "v1", "v2")
    assert diff["added"]["nodes"]
    assert any(n["id"].startswith("evidencia") or n["type"] == "evidencia" for n in diff["added"]["nodes"])


def test_get_graph_retorna_versao_mais_recente(store):
    from ai_microservice.graph.builder import GraphBuilder

    b1 = GraphBuilder(store=store, project_id="PRJ01")
    b1.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b1.save_version(catalog_version="1.0.0", model="m")
    b2 = GraphBuilder(store=store, project_id="PRJ01")
    b2.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b2.add_evidence(regra_id="CRI-D1", fonte="evidencias/metodo.md#2", quote="q3", polaridade="sustenta", natureza="sintese", justificativa="j3")
    b2.save_version(catalog_version="1.0.0", model="m")
    g = store.get_graph("PRJ01")
    ids = {n["id"] for n in g["nodes"]}
    assert any("CRI-D1" in i for i in ids), "get_graph deve voltar a versão mais recente"


def test_tipos_de_no_e_aresta(store):
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ01")
    b.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q1", polaridade="sustenta", natureza="sintese", justificativa="j")
    b.add_gap(regra_id="NOV-D3", motivo="sem evidência após busca")
    b.add_web_source(url="https://exemplo.com", trecho="trecho citado", captured_at="2026-10-08")
    b.add_query(original="PRJ01 deduplicação", sanitized="deduplicação de mensagens", rule_id="NOV-W3")
    g = b.build()
    types = {n.type for n in g.nodes}
    assert {"projeto", "criterio", "regra", "evidencia", "fonte", "gap", "query", "web_source"} <= types
    edges = {e.type for e in g.edges}
    assert {"sustenta", "cita", "compoe", "retornou"} <= edges