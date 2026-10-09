"""CHK-FALHAS (pre-pass) — versões com falha/piora; tipo (operacional × experimental) fica para o especialista.

Falha/piora determinística: taxa < 100 em contagem de desempenho, ou valor
que piora entre versões consecutivas da mesma métrica — respeitando a DIREÇÃO
da métrica (V9.1): para métricas de erro/falha/latência/perda (falsos alertas,
vínculos falsos, fraudes não detectadas, latência), MENOR é melhor; só marca
piora quando o valor sobe na direção errada.
"""
from __future__ import annotations

import re

from ai_microservice.extraction.parsers import Fragment

# métrica cujo NOME casa aqui é menor-é-melhor
_LOWER_IS_BETTER_RE = re.compile(
    r"falso[s]?|erro[s]?|falha[s]?|lat[êe]ncia|perda|piora|indevid[oa][s]?|"
    r"incorporad[oa]s?|contaminad[oa]s?|vazamento[s]?|n[ãa]o detectad[oa]s?",
    re.I,
)


def metric_direction(metrica: str) -> str:
    """maior_e_melhor | menor_e_melhor (pelo nome da métrica, determinístico)."""
    return "menor_e_melhor" if _LOWER_IS_BETTER_RE.search(metrica or "") else "maior_e_melhor"


def _f(v: object) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


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
        taxa_f = _f(taxa)
        if taxa_f is None:
            continue
        if taxa_f < 100:
            com_falha.add(str(r.get("versao")))
            falhas.append({
                "versao": r.get("versao"),
                "ensaio_id": r.get("ensaio_id"),
                "metrica": r.get("metrica"),
                "taxa": taxa_f,
                "descricao_base": r.get("descricao_base"),
            })

    # piora entre versões da mesma métrica, respeitando a direção
    #
    # ordem por versão: a sufixação ("-v1" < "-v2") põe 'condicionado-v4' antes de
    # 'continuo-v3' por erro lexicográfico (v3 > v4 como string). A cronologia do
    # pacote define a ordem real de ensaio; usar posição em cronologia.csv quando
    # disponível, senão número da versão.
    versoes_crono: list[str] = []
    for f in fragments:
        if f.artifact == "evidencias/cronologia.csv":
            v = str((f.data or {}).get("versao") or "")
            if v and v not in versoes_crono:
                versoes_crono.append(v)

    def _versao_key(nome: object) -> tuple[int, str]:
        s = str(nome)
        if s in versoes_crono:
            return (versoes_crono.index(s), s)
        m = re.search(r"-v(\d+)$", s)
        return (int(m.group(1)) if m else 0, s)

    por_metrica: dict[str, list[dict]] = {}
    for r in resultados:
        if (r.get("natureza") or "") == "desempenho":
            por_metrica.setdefault(str(r.get("metrica")), []).append(r)
    pioras: list[dict] = []
    direcao: dict[str, str] = {}
    for metrica, rows in por_metrica.items():
        if len(rows) < 2:
            continue
        direcao[metrica] = metric_direction(metrica)
        rows_sorted = sorted(rows, key=lambda r: _versao_key(r.get("versao")))
        vals = [_f(r.get("valor")) for r in rows_sorted]
        if not vals or any(v is None for v in vals):
            continue
        typed = [v for v in vals if v is not None]
        for i in range(1, len(typed)):
            antes, depois = typed[i - 1], typed[i]
            piorou = depois < antes if direcao[metrica] == "maior_e_melhor" else depois > antes
            if piorou and antes != depois:
                pioras.append({
                    "metrica": metrica,
                    "versao_de": rows_sorted[i - 1].get("versao"),
                    "versao_para": rows_sorted[i].get("versao"),
                })

    return {
        "versoes_com_falha_ou_piora": sorted(com_falha | {str(p["versao_para"]) for p in pioras}),
        "falhas_por_taxa": falhas,
        "pioras": pioras,
        "direcao": direcao,
        "nota": (
            "classificar tipo operacional × experimental é papel do especialista (INC-D4/INC-D9); "
            "piora considera direção da métrica (menor-é-melhor para falsos/erros/latência/perda)"
        ),
    }