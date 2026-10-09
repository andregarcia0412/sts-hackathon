"""CHK-PERGUNTA (pre-pass) — sinal de rotina: pergunta que já nomeia a solução conhecida.

Regra derivada dos históricos (Padrão de Análise §3): "a pergunta registrada já nomeia a
solução" é marca de rotina (PRJ01: "Como aplicar idempotência CONHECIDA…"; PRJ12: "cofre
de chaves CONTRATADO"). Pergunta técnica aberta é marca de incerteza (PRJ02/03/13/18).
Detector calibrado na massa 2026-10-08: dispara em 2/20, zero falso positivo.
"""
from __future__ import annotations

import re

from ai_microservice.extraction.parsers import Fragment

# marcador de solução conhecida dentro do texto da pergunta
_MARCADOR_RE = re.compile(
    r"\b(conhecid[oa]s?|existente[s]?|contratad[oa]s?|dispon[íi]ve(li)?s?|admitid[oa]s?)\b",
    re.I,
)
_PERGUNTA_RE = re.compile(r"Pergunta:\s*(.+)")


def run_chk_pergunta(fragments: list[Fragment]) -> dict:
    """Extrai perguntas de atividades.csv/xlsx e marca solução-conhecida.

    CSV e XLSX são espelhos: dedupe pelo texto da pergunta (csv entra primeiro
    na ordenação de arquivos, e fica como fonte citável do hit).
    """
    perguntas: list[dict] = []
    seen: set[str] = set()
    for f in fragments:
        if f.artifact not in ("atividades.csv", "atividades.xlsx"):
            continue
        saida = str((f.data or {}).get("resultado_ou_saida") or "")
        m = _PERGUNTA_RE.search(saida)
        if not m:
            continue
        texto = re.sub(r"\s+", " ", m.group(1)).strip()
        chave = texto.lower()
        if chave in seen:
            continue
        seen.add(chave)
        marcador = _MARCADOR_RE.search(texto)
        perguntas.append(
            {
                "pergunta": texto,
                "marcador": marcador.group(0).lower() if marcador else None,
                "aplica_solucao_conhecida": marcador is not None,
                "fonte": f.anchor,
            }
        )
    return {
        "chk": "CHK-PERGUNTA",
        "perguntas": perguntas,
        "aplica_solucao_conhecida": any(p["aplica_solucao_conhecida"] for p in perguntas),
        "nota": (
            "pergunta que JÁ NOMEIA a solução conhecida é sinal de rotina (INC-D2 deve "
            "contratar); pergunta aberta é sinal de incerteza — classificação final é do especialista"
        ),
    }