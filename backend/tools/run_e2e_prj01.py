"""E2E do PRJ01 — pipeline completo com LLM real e grafo versionado.

Uso: cd backend && .venv/bin/python tools/run_e2e_prj01.py [--no-llm]

Com --no-llm roda só a parte determinística (parse + checagens + grafo com
regras especiais) para verificação rápida sem custo de API.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "src"))

from ai_microservice.catalog import load_catalog  # noqa: E402
from ai_microservice.config import get_settings  # noqa: E402
from ai_microservice.extraction.parsers import parse_project  # noqa: E402
from ai_microservice.graph.builder import GraphBuilder  # noqa: E402
from ai_microservice.graph.store import JSONFileGraphStore  # noqa: E402

PRJ01 = BACKEND / "data" / "casos_test" / "PRJ01"


def deterministic_part() -> dict:
    parsed = parse_project(PRJ01)
    from ai_microservice.checks.runner import run_all_checks

    checks = run_all_checks(parsed["fragments"])
    catalog = load_catalog()
    s = get_settings()
    builder = GraphBuilder(store=JSONFileGraphStore(base_dir=s.graphs_dir), project_id="PRJ01")
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


async def full_part() -> dict:
    from ai_microservice.agents.orchestrator import run_analysis

    return await run_analysis(PRJ01, analysis_id="e2e-prj01")


def verify_graph(version_expect: str | None = None) -> dict:
    """Critérios de aceite 2–6 da spec, verificados no grafo gerado."""
    s = get_settings()
    store = JSONFileGraphStore(base_dir=s.graphs_dir)
    g = store.get_graph("PRJ01")
    nodes, edges = g["nodes"], g["edges"]
    by_id = {n["id"]: n for n in nodes}
    evs = [n for n in nodes if n["type"] == "evidencia"]
    gaps = [n for n in nodes if n["type"] == "gap"]
    queries = [n for n in nodes if n["type"] == "query"]
    web_sources = [n for n in nodes if n["type"] == "web_source"]

    report = {
        "version": g["version"],
        "nodes": len(nodes),
        "edges": len(edges),
        "evidencias": len(evs),
        "gaps": len(gaps),
        "queries": len(queries),
        "web_sources": len(web_sources),
        "tipos": {},
    }
    for n in nodes:
        report["tipos"][n["type"]] = report["tipos"].get(n["type"], 0) + 1

    # critério 2: toda evidência com citação válida — revalidamos com o gate
    parsed = parse_project(PRJ01)
    frag_text = {f.anchor: f.text for f in parsed["fragments"]}
    from ai_microservice.gate import quote_in_source

    invalid = []
    for n in evs:
        fonte = n["props"].get("fonte", "")
        quote = n["props"].get("quote", "")
        if fonte.startswith("http"):
            continue  # web: validada na origem pelo próprio tool (trecho retornado)
        if fonte not in frag_text or not quote_in_source(quote, frag_text.get(fonte, "")):
            invalid.append({"id": n["id"], "fonte": fonte, "quote": quote[:60]})
    report["citations_invalid"] = invalid

    # critério 4: N/A/parciais/absorvidas no grafo com motivo
    catalog = load_catalog()
    from ai_microservice.catalog import RuleStatus

    especiais = [
        r for r in catalog.rules
        if r.criterion in ("novidade", "criatividade", "incerteza", "sistematizacao", "reprodutibilidade")
        and r.status != RuleStatus.aplicavel
    ]
    regras_no_grafo = {n["label"] for n in nodes if n["type"] == "regra"}
    faltando = [r.id for r in especiais if r.id not in regras_no_grafo]
    report["regras_especiais_faltando"] = faltando

    # critério 3: queries persistidas com original × sanitizada
    bad_queries = [q["id"] for q in queries if not q["props"].get("original") or not q["props"].get("sanitized")]
    report["queries_invalidas"] = bad_queries

    # critério 5: 5 camadas presentes
    layers = {"projeto", "criterio", "regra", "evidencia", "fonte"}
    report["camadas_ok"] = layers <= set(report["tipos"])
    report["criterios"] = sorted({n["label"] for n in nodes if n["type"] == "criterio"})

    return report


def main():
    no_llm = "--no-llm" in sys.argv
    if no_llm:
        part = deterministic_part()
        print(json.dumps({k: v for k, v in part.items() if k != "checks"}, ensure_ascii=False, indent=2, default=str))
    else:
        result = asyncio.run(full_part())
        print("=== RESULTADO ORCHESTRATOR ===")
        print(json.dumps({
            "analysis_id": result["analysis_id"],
            "project_id": result["project_id"],
            "version": result["version"],
            "por_criterio": {
                r.get("criterio"): {
                    "status": r.get("status", "ok"),
                    "regras": [
                        {"id": o.regra_id, "status": o.status_execucao, "evidencias": len(o.evidencias)}
                        for o in r.get("regras", [])
                    ] if "regras" in r else None,
                    "erro": r.get("erro"),
                }
                for r in result["resultados"]
            },
        }, ensure_ascii=False, indent=2, default=str))
    print("=== VERIFICAÇÃO DO GRAFO ===")
    print(json.dumps(verify_graph(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()