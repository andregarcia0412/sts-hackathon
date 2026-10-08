"""CHK-RECALC — recompute medicoes → resultados (o "livro-caixa da verdade").

Operações do dicionário (configuracao.json → operacoes_resultados):
- contagem: somar numeradores/denominadores das medições do MESMO ensaio;
- media / mediana / diferenca_maior_menor / percentil_95 / valor_observado /
  indicador_precalculado.

Saída por linha de resultados: batendo / nao_batendo / vazio (nunca zero).
"""
from __future__ import annotations

import math
from typing import Any

from ai_microservice.extraction.parsers import Fragment


def compare_values(rebuilt: Any, declared: Any) -> str:
    """batendo | nao_batendo | vazio — célula vazia nunca vira 0."""
    if rebuilt is None and declared is None:
        return "vazio"
    if rebuilt is None or declared is None:
        # um lado vazio: só é 'vazio' se não houver o que comparar
        return "vazio" if (rebuilt is None or declared is None) else "nao_batendo"
    try:
        a = float(str(rebuilt).replace(",", "."))
        b = float(str(declared).replace(",", "."))
    except (TypeError, ValueError):
        return "batendo" if str(rebuilt).strip() == str(declared).strip() else "nao_batendo"
    if math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6):
        return "batendo"
    return "nao_batendo"


def _num(v: Any) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _recompute(operacao: str, regs: list[dict], resultado: dict) -> tuple[Any, Any]:
    """Retorna (valor_recalculado, base_recalculada)."""
    if operacao == "contagem":
        num = sum(_num(r.get("numerador")) or 0 for r in regs)
        den = sum(_num(r.get("denominador")) or 0 for r in regs)
        return (num if num is not None else None), (den if den else None)
    valores = [_num(r.get("valor")) for r in regs]
    valores = [v for v in valores if v is not None]
    if operacao == "media":
        n = len(valores)
        return (sum(valores) / n if n else None), (n or None)
    if operacao == "mediana":
        if not valores:
            return None, 0
        s = sorted(valores)
        mid = len(s) // 2
        med = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
        return med, len(s)
    if operacao == "diferenca_maior_menor":
        if not valores:
            return None, 0
        return max(valores) - min(valores), len(valores)
    if operacao == "percentil_95":
        # histograma: valor = ponto, peso = frequência
        pares = [(_num(r.get("valor")), _num(r.get("peso")) or 1) for r in regs]
        pares = [(v, p) for v, p in pares if v is not None]
        if not pares:
            return None, 0
        total = sum(p for _, p in pares)
        posto = math.ceil(0.95 * total)
        acc = 0
        for v, p in sorted(pares):
            acc += p
            if acc >= posto:
                return v, int(total)
        return max(v for v, _ in pares), int(total)
    if operacao == "valor_observado":
        return (valores[0] if valores else None), (1 if valores else None)
    if operacao == "indicador_precalculado":
        # transcrição: conferimos a transcrição, não o cálculo original
        return (valores[0] if valores else None), (1 if valores else None)
    return None, None


def run_chk_recalc(fragments: list[Fragment]) -> dict:
    medicoes: dict[str, list[dict]] = {}
    resultados: list[dict] = []
    for f in fragments:
        if f.artifact == "evidencias/medicoes.csv" and "registros" in f.data:
            medicoes[f.anchor.split("#")[1]] = f.data["registros"]
        elif f.artifact == "evidencias/resultados.csv":
            resultados.append(f.data)

    rows: list[dict] = []
    for r in resultados:
        ensaio = r.get("ensaio_id")
        operacao = (r.get("operacao") or "").strip()
        regs = medicoes.get(ensaio, [])
        if not regs:
            rows.append({
                "ensaio_id": ensaio, "operacao": operacao, "resultado": "vazio",
                "motivo": "sem medições para o ensaio", "valor_recalculado": None,
                "base_recalculada": None, "valor_declarado": r.get("valor"),
            })
            continue
        valor_r, base_r = _recompute(operacao, regs, r)
        res_valor = compare_values(valor_r, r.get("valor"))
        res_base = compare_values(base_r, r.get("base_de_calculo"))
        resultado = "batendo" if (res_valor == "batendo" and res_base == "batendo") else (
            "vazio" if ("vazio" in (res_valor, res_base)) else "nao_batendo"
        )
        rows.append({
            "ensaio_id": ensaio,
            "operacao": operacao,
            "resultado": resultado,
            "valor_recalculado": valor_r,
            "base_recalculada": base_r,
            "valor_declarado": r.get("valor"),
            "base_declarada": r.get("base_de_calculo"),
        })

    status = "ok"
    if rows and all(r["resultado"] == "vazio" for r in rows):
        status = "vazio"
    elif any(r["resultado"] == "nao_batendo" for r in rows):
        status = "divergencia"
    # entrega × desempenho (SIS-D14): natureza e taxa
    for row in rows:
        match = next((r for r in resultados if r.get("ensaio_id") == row["ensaio_id"]), None)
        if match:
            row["natureza"] = match.get("natureza")
            row["taxa_percentual"] = match.get("taxa_percentual")
            if match.get("natureza") == "entrega":
                row["alerta_entrega"] = "contagem de entrega não é desempenho"
    return {"status": status, "rows": rows}