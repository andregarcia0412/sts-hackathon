"""CHK-DIVERG (pre-pass) — números da transcrição × registros (mesma versão, ensaio, denominador).

Extração de números da transcrição é feita por LLM no especialista; aqui o
match determinístico: procuramos os valores declarados de resultados.csv no
texto do depoimento. Quando a extração LLM existir, ela alimenta este match.
"""
from __future__ import annotations

import re

from ai_microservice.extraction.parsers import Fragment

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def run_chk_diverg(fragments: list[Fragment]) -> dict:
    transcricao = ""
    for f in fragments:
        if f.artifact == "transcricao_entrevista_tecnica.pdf":
            transcricao = f.text
            break

    resultados: list[dict] = []
    for f in fragments:
        if f.artifact == "evidencias/resultados.csv":
            resultados.append(f.data)

    divergencias: list[dict] = []
    conferencias: list[dict] = []
    for r in resultados:
        valor = r.get("valor")
        if valor is None or str(valor).strip() == "":
            continue
        # o depoimento menciona o valor do registro para a métrica da mesma versão?
        metrica = (r.get("metrica") or "").lower()
        versao = r.get("versao") or ""
        contexto_depo = transcricao.lower()
        # janela de texto: linha que contém a versão
        linhas = [ln for ln in transcricao.splitlines() if versao and versao in ln]
        janela = "\n".join(linhas) or transcricao
        if str(valor) in janela or str(valor).rstrip("0").rstrip(".") in janela:
            conferencias.append({"ensaio_id": r.get("ensaio_id"), "metrica": r.get("metrica"), "valor": valor, "status": "presente_no_depoimento"})
        else:
            # número declarado não aparece no depoimento — não é divergência
            # (o depoimento pode não mencionar todos); registramos como não mencionado
            conferencias.append({"ensaio_id": r.get("ensaio_id"), "metrica": r.get("metrica"), "valor": valor, "status": "nao_mencionado"})

    # divergência de verdade: número no depoimento que CONTRADIZ o registro
    # (ex.: depoimento diz 12, registro diz 8 na mesma versão) — extraído pelo LLM
    return {
        "divergencias": divergencias,
        "conferencias": conferencias,
        "nota": "extração fina de números do depoimento é do especialista; aqui conferimos presença dos valores do registro",
    }