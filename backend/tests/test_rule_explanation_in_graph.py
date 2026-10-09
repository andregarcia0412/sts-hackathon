"""
Regressão: clicar numa regra da análise IA deve mostrar a EXPLICAÇÃO DA REGRA
(o que ela verifica + fontes normativas), que hoje só existe no catálogo
(GET /regras/{id}) — o grafo guardava só props={"id"}.
"""
import json
from pathlib import Path

from ai_microservice.catalog import load_catalog
from ai_microservice.graph.builder import GraphBuilder
from ai_microservice.graph.schema import Node
from ai_microservice.graph.store import JSONFileGraphStore


def _store(tmp_path):
    return JSONFileGraphStore(base_dir=tmp_path / "graphs")


def test_rule_node_in_graph_carries_what_sources_status(tmp_path):
    """ensure_rule do pipeline grava what/sources/evidence/status/scoring_role."""
    from ai_microservice.catalog import Rule

    rule = Rule(id="INC-D2", criterion="incerteza", block="documento", mode="regra+llm", what="A incerteza é formulada como pergunta técnica?")
    builder = GraphBuilder(store=_store(tmp_path), project_id="PRJ01")
    builder.ensure_rule(rule.id, props=builder.rule_catalog_props(rule))

    node = builder.build().nodes
    rule_node = [n for n in node if n.id == "regra:INC-D2"][0]
    assert rule_node.props["what"] == rule.what
    assert rule_node.props["sources"] == rule.sources
    assert rule_node.props["evidence"] == rule.evidence
    assert rule_node.props["status"] == rule.status.value
    assert rule_node.props["scoring_role"] == rule.scoring_role


def test_rule_node_sem_catalog_props_mantem_id_simples(tmp_path):
    """Chamada antiga props={"id": x} não explode e preserva o id."""
    builder = GraphBuilder(store=_store(tmp_path), project_id="PRJ01")
    builder.ensure_rule("NOV-D1", props={"id": "NOV-D1"})
    node = [n for n in builder.build().nodes if n.id == "regra:NOV-D1"][0]
    assert node.props["id"] == "NOV-D1"


def test_catalogo_tem_sources_para_todas_as_regras_executaveis():
    """Sanidade: regras executáveis do catálogo têm ao menos 1 source (front mostra a referência)."""
    catalog = load_catalog()
    sem_sources = [r.id for r in catalog.rules if r.executes and r.criterion != "transversal" and not r.sources]
    assert not sem_sources, f"regras executáveis sem sources: {sem_sources}"


def test_meta_json_do_grafo(tmp_path):
    """builder: props mescladas — segunda chamada com mais props enriquece o nó."""
    from ai_microservice.catalog import Rule

    rule = Rule(id="SIS-D12", criterion="sistematizacao", block="documento", mode="regra", what="Execução registrada por versão")
    builder = GraphBuilder(store=_store(tmp_path), project_id="PRJ01")
    builder.ensure_rule("SIS-D12", props={"id": "SIS-D12"})  # chamada antiga
    builder.ensure_rule("SIS-D12", props=builder.rule_catalog_props(rule))  # enriquece
    node = [n for n in builder.build().nodes if n.id == "regra:SIS-D12"][0]
    assert node.props["what"] == rule.what
    assert node.props["id"] == "SIS-D12"