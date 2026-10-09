"""Pós-pass de consistência entre critérios (V9.1, ponto 2) — determinístico, no código.

Furo no PRJ01 v1: CRI-D10 "sustenta acoplamento inovador" citando o §1 (manual BARR-2)
enquanto NOV-D4/D10 "contraria: função já fornecida pela referência anterior" — o mesmo
trecho usado nos dois lados, sem checagem cruzada.

Regras:
1. Evidências CONTRARIAS em regras NOV cuja justificativa marca contenção pela referência
   anterior ("já fornece", "anterior", "adaptação de tecnologia"…) marcam a fonte como
   "trecho da referência que contém a função".
2. Toda evidência SUSTENTA de CRI/INC sobre essa mesma fonte é rebaixada para neutra,
   preservando `polaridade_original` + `ajuste_consistencia` (T7 — analista decide).
3. CHK-PERGUNTA com `aplica_solucao_conhecida=True`: evidência SUSTENTA em INC-D2 cujo
   quote contém a pergunta marcada → rebaixada para CONTRARIA (pergunta que já nomeia a
   solução conhecida é sinal de rotina).
"""
from __future__ import annotations

import re

from ai_microservice.graph.builder import GraphBuilder

# justificativa da NOV-contraria que marca "a função está contida na referência anterior"
_CONTENCAO_RE = re.compile(
    r"j[áa] (?:fornec|existe|era| estava)|anterior|adapta[çc][ãa]o de tecnologia|"
    r"j[áa] dominad[oa]|j[áa] conhecid[oa]|tecnologia j[áa] existente|j[áa] admitida",
    re.I,
)

# evidências rebaixadas citam a regra NOV que contratou — auditabilidade
_REBAIXA_NEUTRA = "neutra"
_REBAIXA_CONTRARIA = "contraria"


def run_consistency(builder: GraphBuilder, checks: dict) -> dict:
    graph = builder.build()
    evidencias = [n for n in graph.nodes if n.type == "evidencia" and n.props.get("regra_id")]

    # 1. fontes marcadas por NOV-contraria com contenção
    fontes_contidas: dict[str, str] = {}  # fonte -> regra_id NOV
    for ev in evidencias:
        p = ev.props
        if p.get("regra_id", "").startswith("NOV-") and p.get("polaridade") == "contraria":
            just = p.get("justificativa") or ""
            if _CONTENCAO_RE.search(just):
                fontes_contidas.setdefault(p.get("fonte") or "", p["regra_id"])

    rebaixadas: list[dict] = []
    inc_d2_ajustadas = 0

    # 2. rebaixa sustenta de CRI/INC na mesma fonte
    for ev in evidencias:
        p = ev.props
        rid = p.get("regra_id") or ""
        if not rid.startswith(("CRI-", "INC-")):
            continue
        if p.get("polaridade") != "sustenta":
            continue
        fonte = p.get("fonte") or ""
        if fonte in fontes_contidas:
            nov_rule = fontes_contidas[fonte]
            motivo = (
                f"consistência: fonte também citada por {nov_rule} (contraria) como trecho da "
                f"referência anterior que já fornece a função — não sustenta criatividade/incerteza"
            )
            builder.set_evidence_polarity(ev.id, _REBAIXA_NEUTRA, motivo)
            builder.add_rule_gap(rid, f"ajuste de consistência: {motivo}")
            rebaixadas.append({"regra_id": rid, "fonte": fonte, "de": "sustenta", "para": "neutra", "por": nov_rule})

    # 3. INC-D2 × CHK-PERGUNTA
    chk = checks.get("CHK-PERGUNTA") or {}
    if chk.get("aplica_solucao_conhecida") is True:
        marcadas = [q for q in chk.get("perguntas", []) if q.get("aplica_solucao_conhecida")]
        perguntas = [q.get("pergunta") or "" for q in marcadas]
        fontes = {q.get("fonte") or "" for q in marcadas}
        for ev in evidencias:
            p = ev.props
            if p.get("regra_id") != "INC-D2" or p.get("polaridade") != "sustenta":
                continue
            quote = p.get("quote") or ""
            fonte = p.get("fonte") or ""
            if any(pg.lower() in quote.lower() for pg in perguntas) or fonte in fontes:
                motivo = (
                    "consistência: CHK-PERGUNTA marca a pergunta citada como solução conhecida "
                    "(pergunta que já nomeia a solução é sinal de rotina — históricos PRJ01/PRJ12)"
                )
                builder.set_evidence_polarity(ev.id, _REBAIXA_CONTRARIA, motivo)
                builder.add_rule_gap("INC-D2", f"ajuste de consistência: {motivo}")
                inc_d2_ajustadas += 1
                rebaixadas.append({"regra_id": "INC-D2", "fonte": fonte, "de": "sustenta", "para": "contraria", "por": "CHK-PERGUNTA"})

    return {
        "fontes_contidas": fontes_contidas,
        "rebaixadas": rebaixadas,
        "inc_d2_ajustadas": inc_d2_ajustadas,
    }