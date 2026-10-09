"""Delivery of the cases (spec 08): one folder the jury can open without the application.

Reads a benchmark (and the benchmarks it resumed), the analyses, the graph and the analysts' decisions, and writes
the "Entrega esperada" of the GUIA_DO_PARTICIPANTE item by item. It never writes a decision on anyone's behalf
(principle 1): a project without a decision is marked "pending". The folder contains package excerpts, which are
confidential: it is refused inside a git repository."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from backend.analyses.models import Analysis
from backend.analyses.schemas import AnalysisStatusRead, GraphEdgeRead, GraphNodeRead, GraphRead
from backend.benchmark.models import Benchmark
from backend.benchmark.report_html import report_html
from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.frontend_api.projection import project_analysis
from backend.graph.classify import CLASS_LABELS
from backend.graph.models import GraphEdge, GraphNode
from backend.projects.models import Project
from backend.projects.router import summarize
from backend.projects.schemas import ProjectRead
from backend.report.builder import ANSWER_KEY_COLUMNS, AnalystDecisionInfo, Parecer, build_parecer
from backend.report.export import answer_key_row, to_csv
from backend.report.pdf import render_pdf
from backend.review.models import Contestation, Decision

PENDING = "sugestão — pendente de decisão do analista"
EXPECTED_ITEMS = [
    ("classificação recomendada", "respostas_*.csv (classificacao) · resumo.html · PRJxx/parecer.pdf"),
    ("avaliação dos cinco critérios", "PRJxx/criterios.csv · respostas_*.csv (criterio_n, estado_n, justificativa_n)"),
    ("recorte sustentado, limitação e evidência necessária (Com ressalvas)", "PRJxx/parecer.json (ressalva) · parecer.pdf"),
    ("elo ausente e evidências a solicitar (Evidência insuficiente)", "PRJxx/parecer.json (elo_ausente) · lacunas.csv"),
    ("evidências utilizadas, por ID", "PRJxx/evidencias.csv (fonte = ID do fragmento)"),
    ("evidências contrárias ou contraditórias, inclusive depoimento × documento", "PRJxx/contrarias_e_divergencias.csv"),
    ("lacunas identificadas", "PRJxx/lacunas.csv"),
    ("justificativa da conclusão", "PRJxx/parecer.pdf · respostas_*.csv (justificativa)"),
    ("rastreabilidade: regra aplicada, informação que sustenta, quem decidiu e quando",
     "PRJxx/rastreabilidade.json · PRJxx/grafo.json · parecer.pdf (decisão do analista)"),
]


class DeliveryError(RuntimeError):
    pass


class ProjectOutcome(BaseModel):
    code: str
    status: str  # "ok" | "falhou"
    analysis_id: str | None = None
    suggested_class: str | None = None
    decision: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class DeliveryResult(BaseModel):
    folder: str
    projects: list[ProjectOutcome]
    ok: bool


def inside_git_repository(path: Path) -> bool:
    current = path.resolve()
    for folder in (current, *current.parents):
        if (folder / ".git").exists():
            return True
    return False


def _camel(value):
    if isinstance(value, dict):
        return {to_camel(k) if isinstance(k, str) else k: _camel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_camel(v) for v in value]
    return value


def _csv(header: list[str], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(header)
    writer.writerows(rows)
    return "﻿" + buffer.getvalue()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _benchmarks_chain(benchmark: Benchmark) -> list[Benchmark]:
    chain, current = [benchmark], benchmark
    while current.config.resumed_from:
        current = await Benchmark.get(PydanticObjectId(current.config.resumed_from))
        if current is None:
            break
        chain.append(current)
    return chain


async def latest_analyses(benchmark: Benchmark) -> tuple[dict[str, Analysis], list[str]]:
    """code → the finished analysis to deliver (the newest benchmark wins), plus the codes without one."""
    chosen: dict[str, Analysis] = {}
    codes: list[str] = []
    for item in await _benchmarks_chain(benchmark):
        for run in item.runs:
            if run.code not in codes:
                codes.append(run.code)
            if run.code in chosen:
                continue
            analysis = await Analysis.get(PydanticObjectId(run.analysis_id))
            if analysis is not None and analysis.status == "concluida":
                chosen[run.code] = analysis
    return chosen, [c for c in codes if c not in chosen]


async def _decisions(project_id: str) -> list[Decision]:
    return await Decision.find(Decision.project_id == project_id).sort(+Decision.decided_at).to_list()


def _evidence_rows(analysis: Analysis) -> list[list]:
    return [[e.id, e.rule_id, e.criterion, e.polarity, e.source_id, e.source_alias, e.quote, e.nature, e.origin,
             e.url or "", e.explanation]
            for result in analysis.criteria.values() for run in result.rules for e in run.evidences]


async def frontend_payloads(catalog: Catalog, analysis: Analysis, project: Project, parecer: Parecer) -> dict:
    """What the API would answer for this project, by route — so the front can run on static data."""
    nodes = await GraphNode.find(GraphNode.analysis_id == str(analysis.id)).to_list()
    edges = await GraphEdge.find(GraphEdge.analysis_id == str(analysis.id)).to_list()
    graph = GraphRead(analysis_id=str(analysis.id),
                      nodes=[GraphNodeRead(node_id=n.node_id, kind=n.kind, label=n.label, props=n.props) for n in nodes],
                      edges=[GraphEdgeRead(source=e.source, target=e.target, kind=e.kind, props=e.props) for e in edges])
    contestations = await Contestation.find(Contestation.analysis_id == str(analysis.id)).to_list()
    view = project_analysis(catalog, analysis, project, contestations)
    decisions = [{**d.model_dump(mode="json", exclude={"id", "revision_id"}), "id": str(d.id)}
                 for d in await _decisions(str(project.id))]
    pid, aid = str(project.id), str(analysis.id)
    return {
        f"GET /projects/{pid}": ProjectRead.of(project).model_dump(mode="json", by_alias=True),
        f"GET /projects/{pid}/analyses": [view.model_dump(mode="json", by_alias=True)],
        f"GET /projects/{pid}/decisions": _camel(decisions),
        f"GET /analyses/{aid}/status": AnalysisStatusRead.of(analysis).model_dump(mode="json", by_alias=True),
        f"GET /analyses/{aid}/graph": graph.model_dump(mode="json", by_alias=True),
        f"GET /analyses/{aid}/report.json": _camel(parecer.model_dump(mode="json")),
    }


def _write(folder: Path, name: str, content: str | bytes) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _validate(code: str, parecer: Parecer, analysis: Analysis) -> list[str]:
    warnings = list(parecer.incompleto)
    row = answer_key_row(parecer)
    if list(row) != ANSWER_KEY_COLUMNS:
        warnings.append("linha do CSV fora do esquema de 27 colunas")
    if parecer.classe_sugerida is None:
        warnings.append("sem classe automática")
    for result in analysis.criteria.values():
        for run in result.rules:
            for item in run.evidences:
                if not (item.quote.strip() and item.source_id):
                    warnings.append(f"evidência {item.id} sem trecho literal ou sem fonte")
    return warnings


async def export_delivery(benchmark: Benchmark, catalog: Catalog, out: Path, expected: int | None = None,
                          require_decisions: bool = False) -> DeliveryResult:
    if inside_git_repository(out):
        raise DeliveryError(f"{out} fica dentro de um repositório git: a entrega contém trechos do pacote "
                            "confidencial e não pode entrar no repositório")
    out.mkdir(parents=True, exist_ok=True)
    analyses, missing = await latest_analyses(benchmark)
    outcomes: list[ProjectOutcome] = [ProjectOutcome(code=code, status="falhou", error="sem análise concluída")
                                      for code in missing]
    rows, full, api = [], [], {}
    summaries = []
    for code in sorted(analyses):
        analysis = analyses[code]
        project = await Project.get(PydanticObjectId(analysis.project_id))
        decisions = await _decisions(analysis.project_id)
        infos = [AnalystDecisionInfo(outcome=d.outcome, justification=d.justification, analyst_name=d.analyst_name,
                                     decided_at=d.decided_at) for d in decisions]
        parecer = build_parecer(catalog, analysis, infos, title=analysis.report.get("titulo") if analysis.report else None,
                                code=code)
        decision = CLASS_LABELS.get(decisions[-1].outcome, decisions[-1].outcome) if decisions else None
        outcome = ProjectOutcome(code=code, status="ok", analysis_id=str(analysis.id),
                                 suggested_class=parecer.classificacao, decision=decision,
                                 warnings=_validate(code, parecer, analysis))
        if not decisions:
            outcome.warnings.append(PENDING)
        outcomes.append(outcome)
        folder = out / code
        _write(folder, "parecer.pdf", render_pdf(parecer))
        _write(folder, "parecer.json", parecer.model_dump_json(indent=1))
        _write(folder, "criterios.csv", _csv(
            ["criterio", "estado_sugerido", "coluna", "score", "gates_aplicados", "regra_de_decisao", "justificativa"],
            [[catalog.criteria[c].nome, s.state or "", s.column or "", analysis.criterion_scores.get(c),
              " | ".join(s.gates), s.decision_rule or "", s.justification]
             for c in CRITERIA_ORDER if (s := analysis.states.get(c))]))
        _write(folder, "evidencias.csv", _csv(
            ["id", "regra", "criterio", "polaridade", "fonte_id", "fonte", "trecho_literal", "natureza", "origem",
             "url", "justificativa"], _evidence_rows(analysis)))
        contrary = [[e.id, e.rule_id, e.source_alias, e.quote, e.explanation, ""]
                    for r in analysis.criteria.values() for run in r.rules for e in run.evidences
                    if e.polarity == "negativa"]
        contrary += [["divergência", d.criterion, d.record_alias, d.record_quote, d.testimony_quote, d.statement]
                     for r in analysis.criteria.values() for d in r.divergences]
        _write(folder, "contrarias_e_divergencias.csv", _csv(
            ["id", "regra_ou_criterio", "fonte", "trecho_do_registro", "explicacao_ou_depoimento", "frase"], contrary))
        gaps = [[g.regra, g.status, g.motivo] for g in parecer.lacunas]
        gaps += [["elo ausente", "", link] for link in parecer.elos_ausentes]
        if parecer.elo_ausente and parecer.elo_ausente.elo_ausente:
            gaps.append(["elo ausente (classe)", "", parecer.elo_ausente.elo_ausente + " — solicitar: "
                         + ", ".join(parecer.elo_ausente.evidencias_a_solicitar)])
        _write(folder, "lacunas.csv", _csv(["regra", "status", "motivo"], gaps))
        _write(folder, "rastreabilidade.json", json.dumps({
            "analysis_id": str(analysis.id), "versao_da_analise": analysis.version,
            "versoes": analysis.versions.model_dump(mode="json"),
            "regras_aplicadas": sorted({run.rule_id for r in analysis.criteria.values() for run in r.rules}),
            "decisoes": [{"quem": d.analyst_name, "quando": d.decided_at.isoformat(), "decisao": d.outcome,
                          "justificativa": d.justification, "sugestao_no_momento": d.suggested_class}
                         for d in decisions] or PENDING,
        }, ensure_ascii=False, indent=1))
        payloads = await frontend_payloads(catalog, analysis, project, parecer)
        _write(folder, "grafo.json", json.dumps(payloads[f"GET /analyses/{analysis.id}/graph"], ensure_ascii=False))
        _write(folder, "api.json", json.dumps(payloads, ensure_ascii=False))
        api |= payloads
        summaries.append((await summarize(project)).model_dump(mode="json", by_alias=True))
        row = answer_key_row(parecer)
        if not decisions:
            row["classificacao"] = f"{row['classificacao']} ({PENDING})" if row["classificacao"] else PENDING
        rows.append(row)
        full.append(parecer.model_dump(mode="json") | {"decisao_do_analista": decision or PENDING})
    if expected is not None and len(analyses) < expected:
        outcomes.append(ProjectOutcome(code="(lote)", status="falhou",
                                       error=f"{len(analyses)} de {expected} projetos com análise concluída"))
    if require_decisions:
        for outcome in outcomes:
            if outcome.status == "ok" and outcome.decision is None:
                outcome.status, outcome.error = "falhou", "sem decisão do analista (--require-decisions)"

    span = f"{min(analyses)}-{max(analyses)}" if analyses else "vazio"
    _write(out, f"respostas_{span}.csv", to_csv(rows))
    _write(out, f"respostas_{span}.json", json.dumps(full, ensure_ascii=False, indent=1))
    api["GET /projects"] = {"items": summaries, "total": len(summaries), "page": 1, "pageSize": len(summaries),
                            "statusCounts": {}}
    _write(out, "frontend/api_mock.json", json.dumps(api, ensure_ascii=False))
    _write(out, "resumo.html", resumo_html(benchmark, outcomes, analyses))
    if benchmark.metrics:
        _write(out, "metricas.json", benchmark.metrics.model_dump_json(by_alias=True, indent=1))
        _write(out, "metricas.html", report_html(benchmark))
    _write(out, "LEIA-ME.md", leia_me(benchmark, span))
    ok = all(o.status == "ok" for o in outcomes)
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    manifest = {
        "gerado_em": datetime.now(UTC).isoformat(), "benchmark": str(benchmark.id), "ok": ok,
        "catalogo": benchmark.config.catalog_version, "modelos": benchmark.config.models,
        "projetos": [o.model_dump() for o in outcomes],
        "arquivos": {str(p.relative_to(out)): _sha256(p) for p in files},
        "entradas": {code: a.versions.file_hashes for code, a in analyses.items()},
    }
    _write(out, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    return DeliveryResult(folder=str(out), projects=outcomes, ok=ok)


def resumo_html(benchmark: Benchmark, outcomes: list[ProjectOutcome], analyses: dict[str, Analysis]) -> str:
    rows = []
    for o in sorted(outcomes, key=lambda o: o.code):
        analysis = analyses.get(o.code)
        states = " · ".join(f"{c}: {escape(s.state or '-')}" for c, s in (analysis.states.items() if analysis else []))
        link = f'<a href="{o.code}/parecer.pdf">parecer</a>' if o.status == "ok" else "—"
        rows.append(f"<tr><td>{escape(o.code)}</td><td>{escape(o.suggested_class or '—')}</td>"
                    f"<td>{'sim' if analysis and analysis.suggestion and analysis.suggestion.inconsistent else ''}</td>"
                    f"<td>{states}</td><td>{escape(o.decision or PENDING)}</td>"
                    f"<td>{escape('; '.join(o.warnings + ([o.error] if o.error else [])))}</td><td>{link}</td></tr>")
    return ("<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Entrega</title><style>"
            "body{font:14px/1.4 system-ui,sans-serif;margin:24px;color:#1d2433}table{border-collapse:collapse;width:100%}"
            "th,td{border-bottom:1px solid #e3e6eb;padding:6px 8px;text-align:left;vertical-align:top}"
            "th{background:#f0f2f5}</style></head><body>"
            f"<h1>Entrega — {len(analyses)} pareceres</h1><p>Classe sugerida pelo sistema; a decisão final é do "
            "analista. Os links abrem os arquivos desta pasta, sem internet.</p><table><thead><tr><th>projeto</th>"
            "<th>classe sugerida</th><th>fora do padrão</th><th>estados</th><th>decisão do analista</th>"
            "<th>avisos</th><th>arquivo</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
            f"<p style=\"color:#5b6475\">benchmark {escape(str(benchmark.id))} · catálogo "
            f"{escape(benchmark.config.catalog_version or '-')}</p></body></html>")


def leia_me(benchmark: Benchmark, span: str) -> str:
    items = "\n".join(f"| {item} | {where} |" for item, where in EXPECTED_ITEMS)
    return f"""# Entrega dos casos para análise

Gerada pelo backend a partir do benchmark `{benchmark.id}` (catálogo `{benchmark.config.catalog_version}`).
**O sistema sugere, o analista decide**: a classe de cada parecer é a sugestão do sistema; a decisão final, quando
registrada, aparece com quem decidiu e quando. Projeto sem decisão sai marcado "{PENDING}".

Conteúdo confidencial (trechos do pacote do desafio): não publicar.

## Onde está cada item da "Entrega esperada"

| Item do guia | Arquivo |
|---|---|
{items}

## Arquivos

- `respostas_{span}.csv` — 27 colunas, mesmo esquema de `historicos_classificados.csv` (UTF-8 com BOM, `;`).
- `respostas_{span}.json` — o mesmo, com o parecer completo de cada projeto.
- `resumo.html` — tabela dos projetos com link para cada parecer (abre sem internet).
- `metricas.json` / `metricas.html` — tempo, requisições por modelo, gates, divergências.
- `manifest.json` — sha256 de cada arquivo gerado e dos arquivos de entrada, versões e projetos que falharam.
- `frontend/api_mock.json` e `PRJxx/api.json` — as respostas da API (projeto, análise, grafo, parecer, decisões) por
  rota, para o front rodar sobre dados estáticos.
- `PRJxx/` — `parecer.pdf`, `parecer.json`, `criterios.csv`, `evidencias.csv`, `contrarias_e_divergencias.csv`,
  `lacunas.csv`, `rastreabilidade.json`, `grafo.json`, `api.json`.
"""
