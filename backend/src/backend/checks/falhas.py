"""CHK-FALHAS: performance results that failed or got worse between versions (INC-D4, INC-D9, REP-D3, SIS-D7).

The direction of the metric matters: for "falsos alertas", "latência", "perda", "leitura indevida"... lower is
better, so 7,8 → 5,5 is an improvement. Whether a failure is experimental or operational stays with the LLM."""

import re

from backend.checks.data import cell, number, rows
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject

LOWER_IS_BETTER_RE = re.compile(
    r"fals[oa]s?|erros?\b|falhas?\b|lat[êe]ncia|perd(?:a|as|ido|idos|eu)|piora|indevid[oa]s?|incorporad[oa]s?|"
    r"contaminad[oa]s?|vazamentos?|n[ãa]o detectad[oa]s?|duplicad[oa]s? (?:liberad|aceit|efetivad)|atraso|"
    r"tempo|custo|rejeitad[oa]s? indevid", re.IGNORECASE)


def direction(metric: str | None) -> str:
    return "menor_e_melhor" if metric and LOWER_IS_BETTER_RE.search(metric) else "maior_e_melhor"


def _version_order(canonical: CanonicalProject) -> dict[str, int]:
    order: dict[str, int] = {}
    for r in sorted(rows(canonical, "cronologia"), key=lambda r: cell(r, "data") or ""):
        if (version := cell(r, "versao")) and version not in order:
            order[version] = len(order)
    return order


def _version_number(version: str | None) -> int:
    match = re.search(r"v(\d+)$", version or "")
    return int(match.group(1)) if match else 0


def _measure(row) -> float | None:
    rate = number(cell(row, "taxa_percentual"))
    return rate if rate is not None else number(cell(row, "valor"))


def check(canonical: CanonicalProject) -> CheckResult:
    results = [r for r in rows(canonical, "resultados") if (cell(r, "natureza") or "desempenho") == "desempenho"]
    if not results:
        return CheckResult(id="CHK-FALHAS", status="nao_aplicavel", notes=["sem resultados de desempenho"])
    order = _version_order(canonical)
    failures, worsening, directions = [], [], {}
    by_metric: dict[str, list] = {}
    for r in results:
        metric = cell(r, "metrica")
        directions[metric] = direction(metric)
        rate = number(cell(r, "taxa_percentual"))
        if rate is not None:
            failed = rate > 0 if directions[metric] == "menor_e_melhor" else rate < 100
            if failed:
                failures.append({"ensaio_id": cell(r, "ensaio_id"), "versao": cell(r, "versao"), "metrica": metric,
                                 "taxa_percentual": cell(r, "taxa_percentual")})
        by_metric.setdefault(metric or "", []).append(r)
    for metric, lines in by_metric.items():
        lines = sorted(lines, key=lambda r: (order.get(cell(r, "versao") or "", 999), _version_number(cell(r, "versao"))))
        for before, after in zip(lines, lines[1:], strict=False):
            a, b = _measure(before), _measure(after)
            if a is None or b is None or cell(before, "versao") == cell(after, "versao"):
                continue
            worse = b > a if directions[metric] == "menor_e_melhor" else b < a
            if worse:
                worsening.append({"metrica": metric, "versao_de": cell(before, "versao"),
                                  "versao_para": cell(after, "versao"), "de": a, "para": b})
    versions = sorted({f["versao"] for f in failures} | {w["versao_para"] for w in worsening} - {None})
    return CheckResult(
        id="CHK-FALHAS", status="alerta" if failures or worsening else "ok",
        facts={"versoes_com_falha_ou_piora": versions, "falhas_por_taxa": failures, "pioras": worsening,
               "direcao": directions},
        fragment_ids=[r.id for r in results],
        notes=["o tipo da falha (experimental ou operacional) é decidido pela leitura do método, não por esta checagem"],
    )
