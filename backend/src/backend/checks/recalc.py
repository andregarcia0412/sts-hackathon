"""CHK-RECALC: rebuilds resultados from medicoes with the operation of each line (REP-D9, REP-D2, SIS-D14).

Counts are summed only within the same trial; an empty cell is `vazio`, never zero."""

import math
import statistics

from backend.checks.data import cell, number, rows, same
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject


def _weighted(values: list[tuple[float, float]], rank: int) -> float:
    position = 0.0
    for value, weight in sorted(values):
        position += weight
        if position >= rank:
            return value
    return sorted(values)[-1][0]


def recompute(operation: str | None, measurements: list) -> tuple[float | None, float | None]:
    """(value, base) recomputed from the measurements of one trial; None when the record does not allow it."""
    op = (operation or "").strip().lower()
    if op == "contagem":
        numerators = [number(cell(m, "numerador")) for m in measurements]
        denominators = [number(cell(m, "denominador")) for m in measurements]
        if not numerators or any(n is None for n in numerators):
            return None, None
        base = None if any(d is None for d in denominators) else sum(denominators)
        return sum(numerators), base
    values = [number(cell(m, "valor")) for m in measurements]
    values = [v for v in values if v is not None]
    if not values:
        return None, None
    if op == "media":
        return statistics.fmean(values), float(len(values))
    if op == "mediana":
        return statistics.median(values), float(len(values))
    if op == "diferenca_maior_menor":
        return max(values) - min(values), float(len(values))
    if op == "percentil_95":
        weighted = [(number(cell(m, "valor")), number(cell(m, "peso")) or 1.0) for m in measurements
                    if number(cell(m, "valor")) is not None]
        total = sum(w for _, w in weighted)
        return _weighted(weighted, math.ceil(0.95 * total)), total
    if op in ("valor_observado", "indicador_precalculado"):
        return values[0], None
    return None, None


def check(canonical: CanonicalProject) -> CheckResult:
    results = rows(canonical, "resultados")
    if not results:
        return CheckResult(id="CHK-RECALC", status="nao_aplicavel", notes=["sem resultados no pacote"])
    by_trial: dict[str, list] = {}
    for measurement in rows(canonical, "medicoes"):
        by_trial.setdefault(cell(measurement, "ensaio_id") or "", []).append(measurement)
    lines, fragment_ids = [], []
    for result in results:
        trial = cell(result, "ensaio_id")
        measurements = by_trial.get(trial or "", [])
        value, base = recompute(cell(result, "operacao"), measurements)
        recorded_value, recorded_base = number(cell(result, "valor")), number(cell(result, "base_de_calculo"))
        checks = [same(recorded_value, value)]
        if base is not None and recorded_base is not None:
            checks.append(same(recorded_base, base))
        if not measurements or any(c is None for c in checks):
            situation = "vazio"
        else:
            situation = "batendo" if all(checks) else "nao_batendo"
        nature = cell(result, "natureza")
        lines.append({
            "ensaio_id": trial, "versao": cell(result, "versao"), "metrica": cell(result, "metrica"),
            "operacao": cell(result, "operacao"), "valor_registrado": cell(result, "valor"),
            "valor_recalculado": value, "base_registrada": cell(result, "base_de_calculo"),
            "base_recalculada": base, "medicoes": len(measurements), "situacao": situation, "natureza": nature,
            "taxa_percentual": cell(result, "taxa_percentual"),
            "alerta_entrega": nature == "entrega",  # delivery count is not performance (SIS-D14)
        })
        fragment_ids += [result.id, *(m.id for m in measurements)]
    mismatches = [line["ensaio_id"] for line in lines if line["situacao"] == "nao_batendo"]
    return CheckResult(
        id="CHK-RECALC", status="alerta" if mismatches else "ok",
        facts={"linhas": lines, "nao_batendo": mismatches,
               "vazio": [line["ensaio_id"] for line in lines if line["situacao"] == "vazio"]},
        fragment_ids=list(dict.fromkeys(fragment_ids)),
    )
