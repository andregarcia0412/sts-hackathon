"""Benchmark report for the pitch (spec 07): one static, self-contained HTML page (no CDN, works offline and as an
attachment). Every number carries its origin in the footer: benchmark id, date, models and catalog version."""

from html import escape

from backend.benchmark.models import Benchmark, BenchmarkMetrics, Distribution
from backend.graph.classify import CLASS_LABELS

CSS = """
body{font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2433;margin:0;background:#f6f7f9}
main{max-width:1040px;margin:0 auto;padding:32px 24px 48px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:17px;margin:32px 0 10px;padding-top:8px;border-top:1px solid #dde1e7}
.sub{color:#5b6475;margin:0 0 20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.tile{background:#fff;border:1px solid #dde1e7;border-radius:8px;padding:14px 16px}
.tile b{display:block;font-size:26px;font-weight:650} .tile span{color:#5b6475;font-size:13px}
table{border-collapse:collapse;width:100%;background:#fff;border:1px solid #dde1e7;border-radius:8px;overflow:hidden}
th,td{padding:7px 10px;border-bottom:1px solid #eef0f3;text-align:left;font-size:14px;vertical-align:top}
th{background:#f0f2f5;font-weight:600} td.n{text-align:right;font-variant-numeric:tabular-nums}
td.hit{background:#e7f4ec;font-weight:600} .bar{height:10px;background:#3b6fd1;border-radius:2px;min-width:1px}
.muted{color:#5b6475} footer{margin-top:36px;color:#5b6475;font-size:12px}
"""


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _num(value, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _minutes(dist: Distribution) -> str:
    return "—" if dist.median is None else f"{_num(dist.median / 60, 1)} min"


def _table(head: list[str], rows: list[list[str]], numeric: set[int] = frozenset()) -> str:
    cells = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f'<td class="{"n" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r))
                   + "</tr>" for r in rows)
    return f"<table><thead><tr>{cells}</tr></thead><tbody>{body or '<tr><td>—</td></tr>'}</tbody></table>"


def _bar(value: float, top: float) -> str:
    width = 0 if not top else max(1, round(220 * value / top))
    return f'<div class="bar" style="width:{width}px"></div>'


def report_html(benchmark: Benchmark) -> str:
    m: BenchmarkMetrics = benchmark.metrics or BenchmarkMetrics()
    official = m.accuracy.get("oficial")
    preliminary = m.accuracy.get("preliminar")
    accuracy = official or preliminary
    tiles = [
        (f"{accuracy.class_hits}/{accuracy.n}" if accuracy else "—",
         f"classe correta ({'gabarito oficial' if official else 'leitura preliminar, não oficial'})"),
        (str(m.safety.false_eligible), "falsos elegíveis (meta: 0)"),
        (_minutes(m.timing.total_s), "tempo mediano por projeto"),
        (f"US$ {_num(m.cost.per_run.median, 3)}" if m.cost.total is not None else "só tokens",
         "custo por parecer" if m.cost.total is not None else "preço não configurado (MODEL_PRICES)"),
    ]
    if m.time_vs_manual:
        tiles.append((_pct(m.time_vs_manual.reduction),
                      f"menos tempo que a análise manual ({_num(m.time_vs_manual.manual_minutes)} min; fonte: "
                      f"{escape(m.time_vs_manual.source)})"))
    html = [f"<h1>{escape(benchmark.name)}</h1>",
            f'<p class="sub">{len(benchmark.snapshots)} análises · o sistema sugere, o analista decide</p>',
            '<div class="tiles">' + "".join(f'<div class="tile"><b>{escape(v)}</b><span>{label}</span></div>'
                                            for v, label in tiles) + "</div>"]

    if accuracy:
        labels = [*CLASS_LABELS.values(), "(sem classe)"]
        rows = [[escape(expected), *[(f"<b>{n}</b>" if expected == got else str(n))
                                     for got in labels for n in [accuracy.confusion.get(expected, {}).get(got, 0)]]]
                for expected in labels if expected in accuracy.confusion]
        html += ["<h2>Matriz de confusão (esperado × sugerido)</h2>",
                 _table(["esperado \\ sugerido", *labels], rows, set(range(1, len(labels) + 1))),
                 f'<p class="muted">macro-F1 {_num(accuracy.macro_f1, 2)} · kappa {_num(accuracy.cohen_kappa, 2)}</p>',
                 "<h2>Acerto por critério (estado exato)</h2>",
                 _table(["critério", "estado exato", "coluna"],
                        [[c, _pct(v), _pct(accuracy.column_accuracy.get(c))] for c, v in accuracy.state_accuracy.items()],
                        {1, 2})]

    top = max((x.calls for x in m.by_model.values()), default=0)
    html += ["<h2>Requisições e tokens por modelo</h2>",
             _table(["modelo", "requisições", "", "falhas", "retries", "tokens de prompt", "tokens de resposta",
                     "latência p50", "latência p95", "papéis"],
                    [[escape(model), _num(x.calls), _bar(x.calls, top), _num(x.failures), _num(x.retries),
                      _num(x.prompt_tokens), _num(x.completion_tokens), f"{_num(x.latency_s.median, 1)} s",
                      f"{_num(x.latency_s.p95, 1)} s", escape(", ".join(f"{r} {n}" for r, n in x.roles.items()))]
                     for model, x in sorted(m.by_model.items(), key=lambda i: -i[1].calls)],
                    {1, 3, 4, 5, 6, 7, 8})]
    html += ["<h2>Tempo por etapa</h2>",
             _table(["etapa", "mediana", "p95", "chamadas ao LLM", "tokens"],
                    [[escape(stage), f"{_num(d.median, 1)} s", f"{_num(d.p95, 1)} s",
                      _num(m.by_stage[stage].calls) if stage in m.by_stage else "0",
                      _num(m.by_stage[stage].prompt_tokens + m.by_stage[stage].completion_tokens)
                      if stage in m.by_stage else "0"] for stage, d in m.timing.stages_s.items()],
                    {1, 2, 3, 4})]
    d = m.defensibility
    html += ["<h2>O que o sistema barrou</h2>",
             _table(["controle", "quantidade"], [
                 ["afirmações com fonte citada", _pct(d.with_source)],
                 ["citações inventadas pelo LLM e descartadas (trecho inexistente)", _num(d.invented_citations_refused)],
                 ["depoimentos recusados como evidência (T9)", _num(d.testimony_refused)],
                 ["fontes posteriores ao início separadas como não estado da arte (T3)",
                  _num(d.later_sources_separated)],
                 ["termos sensíveis removidos das buscas na internet (T6)", _num(d.queries_sanitized_terms_removed)],
                 ["buscas sem termo do domínio barradas", _num(d.queries_ungrounded_dropped)],
                 ["divergências entrevista × registro registradas", _num(d.divergences_recorded)],
                 ["evidências neutralizadas por consistência entre critérios", _num(d.evidences_neutralized)],
                 ["critérios em conflito com o score enviados ao analista", _num(d.criteria_incoherent)],
             ], {1})]
    planted = preliminary or official
    if planted and planted.planted_divergences:
        html += ["<h2>Divergências plantadas encontradas</h2>",
                 f"<p>{planted.planted_divergences_found} de {planted.planted_divergences} "
                 f"({_pct(planted.planted_divergence_recall)}) — referência: {escape(planted.reference)}</p>"]
    config = benchmark.config
    models = ", ".join(f"{role}={model}" for role, model in config.models.items() if model)
    html.append(f"<footer>benchmark {escape(str(benchmark.id))} · {benchmark.created_at:%d/%m/%Y %H:%M} UTC · "
                f"catálogo {escape(config.catalog_version or '-')} · modelos: {escape(models)}"
                + (f" · re-julgamento de {escape(config.rejudged_from)}" if config.rejudged_from else "")
                + "</footer>")
    return ("<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width,initial-scale=1\"><title>{escape(benchmark.name)}</title>"
            f"<style>{CSS}</style></head><body><main>{''.join(html)}</main></body></html>")
