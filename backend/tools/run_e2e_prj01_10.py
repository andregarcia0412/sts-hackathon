"""E2E batch — roda o pipeline completo (LLM real) para os N primeiros casos de teste.

Uso: cd backend && .venv/bin/python tools/run_e2e_prj01_10.py [--no-llm] [--limit N]

Com --no-llm roda só a parte determinística (parse + checagens + grafo com regras
especiais) para verificação rápida sem custo de API. Grafo versionado em
data/graphs/<PRJxx>/vN (nunca sobrescreve).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "src"))

from ai_microservice.catalog import load_catalog  # noqa: E402
from ai_microservice.config import get_settings  # noqa: E402
from ai_microservice.extraction.parsers import parse_project  # noqa: E402
from ai_microservice.graph.builder import GraphBuilder  # noqa: E402
from ai_microservice.graph.store import JSONFileGraphStore  # noqa: E402

CASES_DIR = BACKEND / "data" / "casos_test"
OUT_JSON = BACKEND / "data" / "graphs" / "batch_e2e_prj01_10.json"


def deterministic_part(project_dir: Path, project_id: str) -> dict:
    parsed = parse_project(project_dir)
    from ai_microservice.checks.runner import run_all_checks

    checks = run_all_checks(parsed["fragments"])
    catalog = load_catalog()
    s = get_settings()
    builder = GraphBuilder(store=JSONFileGraphStore(base_dir=s.graphs_dir), project_id=project_id)
    for flag in parsed["flags"]:
        builder.ensure_rule("T12", props={"id": "T12"})
        builder.add_gap(regra_id="T12", motivo=flag)
    from ai_microservice.catalog import RuleStatus

    for r in catalog.rules:
        if r.criterion in ("novidade", "criatividade", "incerteza", "sistematizacao", "reprodutibilidade"):
            if r.status != RuleStatus.aplicavel:
                builder.ensure_rule(r.id, props={"id": r.id, "status": r.status, "status_reason": r.status_reason})
                motivo = (
                    f"absorvida em {r.absorbed_into} — não executa"
                    if r.status == RuleStatus.absorvida
                    else f"{r.status}: {r.status_reason}"
                )
                builder.add_rule_gap(r.id, motivo)
    version = builder.save_version(
        catalog_version=catalog.version, model="deterministico", extra_meta={"modo": "sem-llm"}
    )
    return {"version": version, "checks": checks, "flags": parsed["flags"]}


async def full_part(project_dir: Path, project_id: str) -> dict:
    from ai_microservice.agents.orchestrator import run_analysis

    return await run_analysis(project_dir, analysis_id=f"e2e-batch-{project_id.lower()}")


def verify_graph(project_id: str, version_expect: str | None = None) -> dict:
    """Verificação do grafo persistido (mesmos critérios do run_e2e_prj01)."""
    s = get_settings()
    store = JSONFileGraphStore(base_dir=s.graphs_dir)
    g = store.get_graph(project_id)
    nodes, edges = g["nodes"], g["edges"]
    by_id = {n["id"]: n for n in nodes}
    evs = [n for n in nodes if n["type"] == "evidencia"]
    gaps = [n for n in nodes if n["type"] == "gap"]
    queries = [n for n in nodes if n["type"] == "query"]
    project_dir = CASES_DIR / project_id

    report = {
        "version": g["version"],
        "nodes": len(nodes),
        "edges": len(edges),
        "evidencias": len(evs),
        "gaps": len(gaps),
        "queries": len(queries),
        "tipos": {},
    }
    for n in nodes:
        report["tipos"][n["type"]] = report["tipos"].get(n["type"], 0) + 1

    # evidência citável: quote literal na fonte
    parsed = parse_project(project_dir)
    frag_text = {f.anchor: f.text for f in parsed["fragments"]}
    from ai_microservice.gate import quote_in_source

    invalid = []
    for n in evs:
        fonte = n["props"].get("fonte", "")
        quote = n["props"].get("quote", "")
        if fonte.startswith("http"):
            continue  # web: validada na origem pelo próprio tool
        if fonte not in frag_text or not quote_in_source(quote, frag_text.get(fonte, "")):
            invalid.append({"id": n["id"], "fonte": fonte, "quote": quote[:60]})
    report["citations_invalid"] = invalid

    # regras especiais presentes no grafo
    catalog = load_catalog()
    from ai_microservice.catalog import RuleStatus

    especiais = [
        r for r in catalog.rules
        if r.criterion in ("novidade", "criatividade", "incerteza", "sistematizacao", "reprodutibilidade")
        and r.status != RuleStatus.aplicavel
    ]
    regras_no_grafo = {n["label"] for n in nodes if n["type"] == "regra"}
    report["regras_especiais_faltando"] = [r.id for r in especiais if r.id not in regras_no_grafo]

    bad_queries = [q["id"] for q in queries if not q["props"].get("original") or not q["props"].get("sanitized")]
    report["queries_invalidas"] = bad_queries

    layers = {"projeto", "criterio", "regra", "evidencia", "fonte"}
    report["camadas_ok"] = layers <= set(report["tipos"])
    report["criterios"] = sorted({n["label"] for n in nodes if n["type"] == "criterio"})
    return report


async def main() -> None:
    no_llm = "--no-llm" in sys.argv
    limit = 10
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    project_dirs = sorted(p for p in CASES_DIR.iterdir() if p.is_dir() and p.name.startswith("PRJ"))
    project_dirs = [p for p in project_dirs if int(p.name[3:]) <= limit]
    print(f"=== batch: {len(project_dirs)} casos (PRJ01..PRJ{limit:02d}), no_llm={no_llm} ===", flush=True)

    summary = []
    for pd in project_dirs:
        pid = pd.name
        t0 = time.time()
        entry: dict = {"project_id": pid}
        try:
            if no_llm:
                part = deterministic_part(pd, pid)
                entry["mode"] = "sem-llm"
                entry["version"] = part["version"]
                entry["checks"] = "rodadas"
                entry["flags"] = part["flags"]
            else:
                result = await full_part(pd, pid)
                entry["mode"] = "llm"
                entry["version"] = result["version"]
                por_criterio = {}
                for r in result["resultados"]:
                    por_criterio[r.get("criterio")] = {
                        "status": r.get("status", "ok"),
                        "regras": [
                            {"id": o.regra_id, "status": o.status_execucao, "evidencias": len(o.evidencias)}
                            for o in r.get("regras", [])
                        ] if "regras" in r else None,
                        "erro": r.get("erro"),
                    }
                entry["por_criterio"] = por_criterio
            entry["verificacao"] = verify_graph(pid)
            entry["ok"] = (
                entry["verificacao"]["camadas_ok"]
                and not entry["verificacao"]["regras_especiais_faltando"]
            )
        except Exception as exc:
            entry["ok"] = False
            entry["erro"] = f"{type(exc).__name__}: {exc}"
        entry["segundos"] = round(time.time() - t0, 1)
        summary.append(entry)
        print(f"\n--- {pid}: {'OK' if entry['ok'] else 'FALHOU'} "
              f"(v={entry.get('version')}, {entry['segundos']}s) ---", flush=True)
        print(json.dumps(entry, ensure_ascii=False, indent=2, default=str), flush=True)
        # append-safe: reescreve o JSON acumulado a cada caso
        OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"\n=== RESUMO ===", flush=True)
    for e in summary:
        print(f"{e['project_id']}: {'OK' if e['ok'] else 'FALHOU'} "
              f"v={e.get('version')} {e['segundos']}s", flush=True)
    ok = sum(1 for e in summary if e["ok"])
    print(f"{ok}/{len(summary)} casos OK", flush=True)
    print(f"resumo salvo em {OUT_JSON}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())