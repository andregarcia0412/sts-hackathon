"""CHK-FALHAS (pre-pass) — versões com falha/piora; tipo (operacional × experimental) fica para o especialista.

Falha/piora determinística: taxa < 100 em contagem de desempenho, ou valor
que piora entre versões consecutivas da mesma métrica.
"""
from __future__ import annotations

from ai_microservice.extraction.parsers import Fragment


def run_chk_falhas(fragments: list[Fragment]) -> dict:
    resultados: list[dict] = []
    for f in fragments:
        if f.artifact == "evidencias/resultados.csv":
            resultados.append(f.data)

    # taxa < 100 (ou 0) em contagem de desempenho → falha nessa versão
    com_falha: set[str] = set()
    falhas: list[dict] = []
    for r in resultados:
        if (r.get("natureza") or "") != "desempenho":
            continue
        taxa = r.get("taxa_percentual")
        if taxa is None or str(taxa).strip() == "":
            continue
        try:
            taxa_f = float(str(taxa).replace(",", "."))
        except ValueError:
            continue
        if taxa_f < 100:
            com_falha.add(r.get("versao"))
            falhas.append({
                "versao": r.get("versao"),
                "ensaio_id": r.get("ensaio_id"),
                "metrica": r.get("metrica"),
                "taxa": taxa_f,
                "descricao_base": r.get("descricao_base"),
            })

    # piora entre versões da mesma métrica
    por_metrica: dict[str, list[dict]] = {}
    for r in resultados:
        if (r.get("natureza") or "") == "desempenho":
            por_metrica.setdefault(r.get("metrica"), []).append(r)
    pioras: list[dict] = []
    for metrica, rows in por_metrica.items():
        if len(rows) < 2:
            continue
        try:
            rows_sorted = sorted(rows, key=lambda r: str(r.get("versao")))
            vals = [float(str(r.get("valor")).replace(",", ".")) for r in rows_sorted]
        except (TypeError, ValueError):
            continue
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                pioras.append({
                    "metrica": metrica,
                    "versao_de": rows_sorted[i - 1].get("versao"),
                    "versao_para": rows_sorted[i].get("versao"),
                })

    # classificação do TIPO (operacional × experimental) é feita pelo especialista (LLM),
    # mas damos as pistas: verbo de configuração na descrição/observações
    return {
        "versoes_com_falha_ou_piora": sorted(com_falha | {p["versao_para"] for p in pioras}),
        "falhas_por_taxa": falhas,
        "pioras": pioras,
        "nota": "classificar tipo operacional × experimental é papel do especialista (INC-D4/INC-D9)",
    }