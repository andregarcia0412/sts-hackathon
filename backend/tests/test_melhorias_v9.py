"""Testes das melhorias V9.1 (spec 2026-10-08-revisao-v9-pontos-1-6.md).

Pontos: (1) sinais de rotina (CHK-PERGUNTA + direção de métrica), (2) pós-pass de
consistência, (3) gate de fundamentação, (4) CHK citável, (5) web aterrado com
rule_id, (6) validação de schema + manifest_hash.
"""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
PRJ01 = BACKEND / "data" / "casos_test" / "PRJ01"
PRJ02 = BACKEND / "data" / "casos_test" / "PRJ02"
PRJ12 = BACKEND / "data" / "casos_test" / "PRJ12"
PRJ13 = BACKEND / "data" / "casos_test" / "PRJ13"


@pytest.fixture()
def store(tmp_path):
    from ai_microservice.graph.store import JSONFileGraphStore

    return JSONFileGraphStore(base_dir=tmp_path / "graphs")


# ================================================================ ponto 1
@pytest.fixture(scope="module")
def prj01_parsed():
    from ai_microservice.extraction.parsers import parse_project

    return parse_project(PRJ01)


def test_chk_pergunta_dispara_em_prj01(prj01_parsed):
    from ai_microservice.checks.pergunta import run_chk_pergunta

    out = run_chk_pergunta(prj01_parsed["fragments"])
    assert out["chk"] == "CHK-PERGUNTA"
    assert out["aplica_solucao_conhecida"] is True
    hit = [p for p in out["perguntas"] if p["aplica_solucao_conhecida"]]
    assert len(hit) == 1, "só a pergunta com marcador sinaliza"
    assert "idempotência conhecida" in hit[0]["pergunta"]
    assert hit[0]["marcador"] == "conhecida"
    assert hit[0]["fonte"] == "atividades.csv#PRJ01-ATV01"


def test_chk_pergunta_nao_dispara_em_pergunta_aberta():
    from ai_microservice.extraction.parsers import parse_project
    from ai_microservice.checks.pergunta import run_chk_pergunta

    out = run_chk_pergunta(parse_project(PRJ02)["fragments"])
    assert out["aplica_solucao_conhecida"] is False
    assert out["perguntas"], "PRJ02 tem pergunta, mas aberta"
    assert all(p["marcador"] is None for p in out["perguntas"])


def test_chk_pergunta_dispara_em_prj12():
    from ai_microservice.extraction.parsers import parse_project
    from ai_microservice.checks.pergunta import run_chk_pergunta

    out = run_chk_pergunta(parse_project(PRJ12)["fragments"])
    assert out["aplica_solucao_conhecida"] is True
    assert any(p["marcador"] == "contratado" for p in out["perguntas"])


def test_chk_pergunta_dedupe_csv_xlsx(prj01_parsed):
    """PRJ01 entrega atividades.csv E atividades.xlsx com a mesma pergunta — conta 1."""
    from ai_microservice.checks.pergunta import run_chk_pergunta

    out = run_chk_pergunta(prj01_parsed["fragments"])
    textos = [p["pergunta"] for p in out["perguntas"]]
    assert len(textos) == len(set(textos)), "pergunta repetida entre csv e xlsx não deve duplicar"


def test_chk_falhas_direcao_menor_e_melhor():
    """PRJ13: falsos alertas 7,8→5,5 é MELHORA — não pode constar em pioras."""
    from ai_microservice.extraction.parsers import parse_project
    from ai_microservice.checks.falhas import run_chk_falhas
    from ai_microservice.checks.runner import RUN_CHECKS  # nova checagem registrada

    assert "CHK-PERGUNTA" in RUN_CHECKS
    falhas = run_chk_falhas(parse_project(PRJ13)["fragments"])
    assert falhas["direcao"]["falsos alertas entre legítimas"] == "menor_e_melhor"
    assert not any(
        p["metrica"] == "falsos alertas entre legítimas" for p in falhas["pioras"]
    ), "melhora em métrica menor-é-melhor foi marcada como piora"
    # PRJ01 não muda: v1 66,7% continua em versoes_com_falha_ou_piora (sinal bruto)
    from ai_microservice.extraction.parsers import parse_project as _pp

    prj01 = run_chk_falhas(_pp(PRJ01)["fragments"])
    assert "deduplicacao-v1" in prj01["versoes_com_falha_ou_piora"]


# ================================================================ ponto 3
def test_fundamentacao_ancorada_passa():
    from ai_microservice.gate import valida_justificativa

    ok, motivo = valida_justificativa(
        "O trecho afirma que nenhum algoritmo foi modificado, o que descaracteriza investigação."
    )
    assert ok is True


def test_fundamentacao_especulativa_sem_ancoragem_rejeita():
    from ai_microservice.gate import valida_justificativa

    ok, motivo = valida_justificativa(
        "A mudança da janela pode gerar comportamento inesperado, caracterizando risco tecnológico."
    )
    assert ok is False
    assert "especulativa" in motivo or "ancoragem" in motivo


def test_fundamentacao_especulativa_com_ancoragem_passa():
    from ai_microservice.gate import valida_justificativa

    ok, _ = valida_justificativa(
        "O trecho registra que o ajuste fica na faixa admitida; pode gerar dúvida, mas o texto mostra isso."
    )
    assert ok is True


def test_fundamentacao_curta_rejeita():
    from ai_microservice.gate import valida_justificativa

    ok, motivo = valida_justificativa("é rotina")
    assert ok is False


def test_fundamentacao_vazia_rejeita():
    from ai_microservice.gate import valida_justificativa

    assert valida_justificativa("")[0] is False
    assert valida_justificativa(None)[0] is False


# ================================================================ ponto 6
def test_schema_sem_polaridade_rejeita():
    from ai_microservice.agents.criterion import validate_evidence_schema

    parsed = {"evidencias": [{"fonte": "f", "quote": "q", "justificativa": "j"}]}
    err = validate_evidence_schema(parsed)
    assert err and "polaridade" in err


def test_schema_polaridade_invalida_rejeita():
    from ai_microservice.agents.criterion import validate_evidence_schema

    parsed = {
        "evidencias": [
            {"fonte": "f", "quote": "q", "polaridade": "prova", "justificativa": "j"}
        ]
    }
    assert "polaridade" in validate_evidence_schema(parsed)


def test_schema_lista_vazia_sem_motivo_rejeita():
    from ai_microservice.agents.criterion import validate_evidence_schema

    assert validate_evidence_schema({"evidencias": []})  # exige sem_evidencia_motivo
    assert validate_evidence_schema({"evidencias": [], "sem_evidencia_motivo": "busca sem achados"}) is None


def test_schema_valido_passa():
    from ai_microservice.agents.criterion import validate_evidence_schema

    parsed = {
        "evidencias": [
            {"fonte": "evidencias/metodo.md#2", "quote": "q", "polaridade": "contraria", "justificativa": "j"}
        ]
    }
    assert validate_evidence_schema(parsed) is None


def test_manifest_hash_nao_nulo():
    from ai_microservice.graph.builder import manifest_hash

    files = [{"path": "a.csv", "sha256": "x"}, {"path": "b.json", "sha256": "y"}]
    h1 = manifest_hash(files)
    assert h1 and len(h1) == 64
    assert manifest_hash(list(reversed(files))) == h1, "ordem não deve mudar o hash do conjunto"


# ================================================================ ponto 4
def _fake_rule(rule_id: str):
    from ai_microservice.catalog import Rule

    return Rule(id=rule_id, criterion="incerteza", block="documento", mode="llm", what="w")


def _chk_frag_texts(checks: dict) -> dict:
    from ai_microservice.agents.criterion import CriterionAgent

    return CriterionAgent.chk_fragment_texts(checks)


def test_chk_fonte_citavel_com_quote_do_json():
    checks = {"CHK-CONFIG": {"referencia_anterior_tipo": "manual", "funcao_ja_fornecida": True}}
    texts = _chk_frag_texts(checks)
    from ai_microservice.agents.criterion import CriterionAgent

    agent = CriterionAgent.__new__(CriterionAgent)  # sem LLM: só o validador
    agent._frag_by_anchor = {}
    agent._chk_texts = texts
    ok, _ = agent._validate_evidence(
        _fake_rule("NOV-D4"),
        {"fonte": "chk:CHK-CONFIG", "quote": '"referencia_anterior_tipo": "manual"'},
    )
    assert ok is True


def test_chk_fonte_rejeita_quote_inventado():
    from ai_microservice.agents.criterion import CriterionAgent

    checks = {"CHK-CONFIG": {"funcao_ja_fornecida": True}}
    agent = CriterionAgent.__new__(CriterionAgent)
    agent._frag_by_anchor = {}
    agent._chk_texts = CriterionAgent.chk_fragment_texts(checks)
    ok, motivo = agent._validate_evidence(
        _fake_rule("NOV-D4"),
        {"fonte": "chk:CHK-CONFIG", "quote": '"funcao_ja_fornecida": false'},
    )
    assert ok is False and "chk" in motivo.lower()


def test_evidencia_de_chk_fica_derivada(store):
    """_record força natureza=derivado em evidência de fonte chk:"""
    from ai_microservice.agents.criterion import CriterionAgent
    from ai_microservice.catalog import Rule
    from ai_microservice.graph.builder import GraphBuilder

    builder = GraphBuilder(store=store, project_id="PRJ01")
    agent = CriterionAgent.__new__(CriterionAgent)
    agent.builder = builder
    agent._frag_by_anchor = {}
    agent._chk_texts = {"CHK-CONFIG": '"funcao_ja_fornecida": true'}
    agent.model = "m"
    rule = Rule(id="INC-D12", criterion="incerteza", block="documento", mode="regra+llm", what="w")
    agent._record(
        rule,
        [{"fonte": "chk:CHK-CONFIG", "quote": '"funcao_ja_fornecida": true', "polaridade": "sustenta"}],
        None,
    )
    evs = [n for n in builder.build().nodes if n.type == "evidencia"]
    assert len(evs) == 1 and evs[0].props["natureza"] == "derivado"
    fontes = [n for n in builder.build().nodes if n.type == "fonte" and n.props.get("ancora") == "chk:CHK-CONFIG"]
    assert len(fontes) == 1, "fonte chk deve virar nó citável"


def test_buscar_em_arquivos_nao_devolve_chk_fragmentos(prj01_parsed):
    from ai_microservice.extraction.parsers import Fragment
    from ai_microservice.tools.file_search import search_fragments

    frags = prj01_parsed["fragments"] + [
        Fragment(anchor="chk:CHK-CONFIG", text='{"x": 1}', nature="derivado", artifact="chk:CHK-CONFIG")
    ]
    out = search_fragments(frags, termo="x")
    assert all(not f.anchor.startswith("chk:") for f in out)


# ================================================================ ponto 5
@pytest.mark.asyncio
async def test_web_query_sem_termo_do_dominio_bloqueada():
    from ai_microservice.tools.web import WebTools

    wt = WebTools()
    ground = await _grounded_search(wt, domain_terms={"deduplicacao", "retencao"}, query="open problem in quantum error correction")
    assert ground.startswith("ERRO_QUERY")
    assert wt.query_log == [], "query sem aterramento não deve logar como executada"


@pytest.mark.asyncio
async def test_web_query_com_termo_do_dominio_executa_e_loga_rule_id():
    from ai_microservice.tools import web as web_mod

    wt = web_mod.WebTools()
    # patch: substitui o método no módulo para o teste (sem rede)
    async def _fake(self, query: str, rule_id: str | None = None) -> str:
        sanitized, log_entry = web_mod.sanitize_query(query)
        log_entry["rule_id"] = rule_id
        self.query_log.append(log_entry)
        return f"RESULTADOS para {sanitized}"

    original = web_mod.WebTools.web_search
    web_mod.WebTools.web_search = _fake
    try:
        ground = await _grounded_search(
            wt,
            domain_terms={"deduplicacao", "retencao"},
            query="deduplicacao idempotency retention window",
            rule_id="NOV-W3",
        )
    finally:
        web_mod.WebTools.web_search = original
    assert ground.startswith("RESULTADOS")
    assert wt.query_log and wt.query_log[-1]["rule_id"] == "NOV-W3"


async def _grounded_search(wt, domain_terms: set[str], query: str, rule_id: str | None = None) -> str:
    """Closure equivalente àquela montada pelo CriterionAgent._make_tools."""
    from ai_microservice.tools.web import query_has_domain_term

    if not query_has_domain_term(query, domain_terms):
        return f"ERRO_QUERY: query sem termo do domínio do projeto: {query!r}. Exemplos de termos: {sorted(domain_terms)[:10]}"
    return await wt.web_search(query=query, rule_id=rule_id)


async def _fake_web_search(self, query: str, rule_id: str | None = None) -> str:
    from ai_microservice.tools.web import sanitize_query

    sanitized, log_entry = sanitize_query(query)
    log_entry["rule_id"] = rule_id
    self.query_log.append(log_entry)
    return f"RESULTADOS para {sanitized}"


def test_query_has_domain_term_case_insensitive():
    from ai_microservice.tools.web import query_has_domain_term

    assert query_has_domain_term("Deduplicação de DUPLICATAS", {"duplicatas", "retencao"})
    assert not query_has_domain_term("quantum error correction", {"duplicatas"})


def test_extract_domain_terms_do_pacote(prj01_parsed):
    from ai_microservice.tools.web import extract_domain_terms_from_text

    terms = extract_domain_terms_from_text([f.text for f in prj01_parsed["fragments"]])
    assert isinstance(terms, set) and terms
    assert any("duplic" in t or "reten" in t or "dedup" in t for t in terms), (
        "termos do domínio (deduplicação/retenção/duplicatas) devem constar"
    )
    assert all(len(t) >= 5 for t in terms)
    assert not any(t in terms for t in {"sobre", "para", "como", "entre", "segundo"})


# ================================================================ ponto 2
def _ev_props(regra_id, fonte, quote, polaridade, justificativa):
    return dict(regra_id=regra_id, fonte=fonte, quote=quote, polaridade=polaridade, natureza="sintese", justificativa=justificativa)


def test_consistencia_rebaixa_cri_inc_sustentadas_pela_referencia(store):
    from ai_microservice.agents.consistency import run_consistency
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ01")
    ref = "evidencias/metodo.md#1"
    b.add_evidence(regra_id="NOV-D4", fonte=ref, quote="O manual BARR-2 fornece a função anteriormente.", polaridade="contraria", natureza="registro_primario", justificativa="O trecho demonstra que a função já era fornecida pelo manual anterior ao projeto.")
    b.add_evidence(regra_id="CRI-D10", fonte=ref, quote="O manual BARR-2 fornece a função anteriormente.", polaridade="sustenta", natureza="registro_primario", justificativa="O trecho apresenta combinação original de chave.")
    b.add_evidence(regra_id="INC-D1", fonte="evidencias/metodo.md#2", quote="Outro texto qualquer.", polaridade="sustenta", natureza="sintese", justificativa="O trecho descreve risco técnico.")

    res = run_consistency(b, checks={})
    assert res["rebaixadas"], "CRI-D10 na mesma fonte da NOV-contraria deveria ser rebaixada"
    evs = {n.props.get("regra_id"): n for n in b.build().nodes if n.type == "evidencia"}
    cri = evs["CRI-D10"]
    assert cri.props["polaridade"] == "neutra"
    assert cri.props["polaridade_original"] == "sustenta"
    assert "NOV-D4" in cri.props["ajuste_consistencia"]
    inc = evs["INC-D1"]
    assert inc.props["polaridade"] == "sustenta", "fonte diferente não deve ser tocada"


def test_consistencia_nao_rebaixa_sem_marcador_de_contencao(store):
    from ai_microservice.agents.consistency import run_consistency
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ01")
    b.add_evidence(regra_id="NOV-D1", fonte="evidencias/metodo.md#2", quote="q", polaridade="contraria", natureza="sintese", justificativa="O trecho só declara configuração, sem elemento novo.")
    b.add_evidence(regra_id="CRI-D1", fonte="evidencias/metodo.md#2", quote="q", polaridade="sustenta", natureza="sintese", justificativa="O trecho registra hipótese explícita.")
    run_consistency(b, checks={})
    evs = [n for n in b.build().nodes if n.type == "evidencia" and n.props.get("regra_id") == "CRI-D1"]
    assert evs[0].props["polaridade"] == "sustenta", "NOV-contraria sem marcador de contenção não pode rebaixar"


def test_consistencia_inc_d2_x_chk_pergunta_vira_contraria(store):
    from ai_microservice.agents.consistency import run_consistency
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ01")
    b.add_evidence(
        regra_id="INC-D2",
        fonte="atividades.csv#PRJ01-ATV01",
        quote="Pergunta: Como aplicar idempotência conhecida ao reenvio de mensagens sem bloquear pagamentos legítimos?",
        polaridade="sustenta",
        natureza="registro_primario",
        justificativa="O trecho registra pergunta técnica sobre idempotência.",
    )
    checks = {
        "CHK-PERGUNTA": {
            "aplica_solucao_conhecida": True,
            "perguntas": [{"pergunta": "Como aplicar idempotência conhecida ao reenvio de mensagens sem bloquear pagamentos legítimos?", "marcador": "conhecida", "aplica_solucao_conhecida": True, "fonte": "atividades.csv#PRJ01-ATV01"}],
        }
    }
    res = run_consistency(b, checks=checks)
    evs = [n for n in b.build().nodes if n.type == "evidencia" and n.props.get("regra_id") == "INC-D2"]
    assert evs[0].props["polaridade"] == "contraria"
    assert evs[0].props["polaridade_original"] == "sustenta"
    assert "CHK-PERGUNTA" in evs[0].props["ajuste_consistencia"]
    assert res["inc_d2_ajustadas"] == 1


def test_consistencia_nao_rebaixa_em_pergunta_aberta(store):
    from ai_microservice.agents.consistency import run_consistency
    from ai_microservice.graph.builder import GraphBuilder

    b = GraphBuilder(store=store, project_id="PRJ02")
    b.add_evidence(
        regra_id="INC-D2",
        fonte="atividades.csv#PRJ02-ATV01",
        quote="Pergunta: Era possível associar os registros sem depender de uma igualdade exata entre textos e horários?",
        polaridade="sustenta",
        natureza="registro_primario",
        justificativa="O trecho registra pergunta técnica aberta.",
    )
    checks = {"CHK-PERGUNTA": {"aplica_solucao_conhecida": False, "perguntas": []}}
    run_consistency(b, checks=checks)
    evs = [n for n in b.build().nodes if n.type == "evidencia" and n.props.get("regra_id") == "INC-D2"]
    assert evs[0].props["polaridade"] == "sustenta"