"""Orchestrator (gpt-oss:120b) — paraleliza os 5 especialistas e agrega (spec 5.4).

O papel de LLM aqui é limitado e auditável: a distribuição das regras é
determinística a partir do catálogo. Falha de um especialista não derruba a análise.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from ai_microservice.agents.criterion import CriterionAgent
from ai_microservice.catalog import Catalog, Rule, RuleStatus, load_catalog
from ai_microservice.config import get_settings
from ai_microservice.extraction.parsers import parse_project
from ai_microservice.graph.builder import GraphBuilder
from ai_microservice.graph.store import JSONFileGraphStore
from ai_microservice.tools.web import WebTools

log = logging.getLogger("ai_microservice.orchestrator")

CRITERIA = ["novidade", "criatividade", "incerteza", "sistematizacao", "reprodutibilidade"]
CRITERION_FILES = {
    "novidade": "NOV.md",
    "criatividade": "CRI.md",
    "incerteza": "INC.md",
    "sistematizacao": "SIS.md",
    "reprodutibilidade": "REP.md",
}


def load_handbook(criterion: str, catalog_dir: Path) -> str:
    path = catalog_dir / "handbooks" / CRITERION_FILES[criterion]
    return path.read_text(encoding="utf-8")


def _rules_to_execute(catalog: Catalog) -> list[Rule]:
    return [
        r for r in catalog.rules
        if r.criterion in CRITERIA and r.executes
    ]


def _rules_special(catalog: Catalog) -> dict:
    """N/A, parciais e absorvidas: entram no grafo com motivo, sem execução (critério 4)."""
    out = {"na": [], "parcial": [], "absorvida": []}
    for r in catalog.rules:
        if r.criterion in CRITERIA:
            if r.status == RuleStatus.na:
                out["na"].append(r)
            elif r.status == RuleStatus.parcial:
                out["parcial"].append(r)
            elif r.status == RuleStatus.absorvida:
                out["absorvida"].append(r)
    return out


async def run_analysis(project_path: Path, analysis_id: str, status_cb=None) -> dict:
    """Pipeline completo: parse → checagens → especialistas paralelos → grafo."""
    s = get_settings()

    async def step(name: str):
        if status_cb:
            await status_cb(name, "rodando")

    await step("ingestao")
    parsed = parse_project(Path(project_path))
    project_id = Path(project_path).name

    from ai_microservice.checks.runner import run_all_checks

    await step("checagens")
    checks = run_all_checks(parsed["fragments"])

    await step("interpretação")
    # (o intérprete enriquece o manifest; rodamos em background do pipeline)
    from ai_microservice.extraction.interpreter import enrich_manifest

    manifest = await enrich_manifest(parsed["fragments"], parsed["manifest"])

    catalog = load_catalog()

    builder = GraphBuilder(store=JSONFileGraphStore(base_dir=s.graphs_dir), project_id=project_id)
    for flag in parsed["flags"]:
        builder.ensure_rule("T12", props={"id": "T12"})
        builder.add_gap(regra_id="T12", motivo=flag)

    # regras N/A, parciais e absorvidas com motivo (nunca silêncio)
    await step("regras_especiais")
    special = _rules_special(catalog)
    for kind, rules in special.items():
        for r in rules:
            builder.ensure_rule(r.id, props={"id": r.id, "status": r.status, "status_reason": r.status_reason})
            motivo = f"{r.status}: {r.status_reason}"
            if r.status == RuleStatus.absorvida:
                motivo = f"absorvida em {r.absorbed_into} — não executa"
            builder.add_rule_gap(r.id, motivo)

    # termos do domínio (determinístico): aterram queries web (V9.1)
    from ai_microservice.tools.web import extract_domain_terms_from_text

    _ROTAS_BASES = {rota.split("#")[0] for rule in catalog.rules if rule.executes for rota in rule.routing}
    textos_rota = [
        f.text for f in parsed["fragments"]
        if f.artifact in _ROTAS_BASES and not f.anchor.startswith("chk:")
    ]
    domain_terms = extract_domain_terms_from_text(textos_rota)

    # especialistas em paralelo com semáforo
    await step("especialistas")
    web_tools = WebTools()
    sem = asyncio.Semaphore(s.analyze_concurrency)

    # web só para critérios que têm regras block=web (NOV/CRI/INC); SIS/REP são só-documentos
    _WEB_CRITERIA = {"novidade", "criatividade", "incerteza"}

    async def run_criterion(criterion: str) -> dict:
        async with sem:
            try:
                handbook = load_handbook(criterion, s.catalog_dir)
                agent = CriterionAgent(
                    criterion=criterion,
                    handbook=handbook,
                    catalog=catalog,
                    fragments=parsed["fragments"],
                    checks=checks,
                    builder=builder,
                    model=s.model_analyst,
                    web_tools=web_tools,
                    allow_web=criterion in _WEB_CRITERIA,
                    domain_terms=domain_terms,
                )
                return await agent.run()
            except Exception as exc:
                log.exception("especialista %s falhou", criterion)
                # regras do critério ficam "não executadas" com motivo (spec 5.4)
                for r in catalog.rules_for_criterion(criterion):
                    builder.ensure_rule(r.id, props={"id": r.id, "status": "nao_executada"})
                    builder.add_rule_gap(r.id, f"critério falhou: {type(exc).__name__}: {exc}")
                return {
                    "criterio": criterion,
                    "status": "falhou",
                    "erro": f"{type(exc).__name__}: {exc}",
                }

    results = await asyncio.gather(*(run_criterion(c) for c in CRITERIA))

    # pós-pass de consistência entre critérios (V9.1): fontes marcadas como
    # contidas na referência anterior rebaixam sustenta de CRI/INC; CHK-PERGUNTA
    # contrata INC-D2 com pergunta-nomeia-solução. Determinístico, auditável.
    from ai_microservice.agents.consistency import run_consistency

    await step("consistencia")
    consistencia = run_consistency(builder, checks)

    # queries web persistidas (original × sanitizada) + ligações query → fonte
    await step("web_log")
    for q in web_tools.query_log:
        builder.add_query(
            original=q["original"],
            sanitized=q["sanitized"],
            rule_id=q.get("rule_id"),
            removed=q.get("removed"),
        )

    # regras transversais de design e executáveis ficam como nós com estado
    await step("grafo")
    from ai_microservice.graph.builder import manifest_hash as _manifest_hash

    version = builder.save_version(
        catalog_version=catalog.version,
        model=s.model_analyst,
        extra_meta={
            "analysis_id": analysis_id,
            "manifest": manifest,
            "manifest_hash": _manifest_hash(manifest["files"]),
            "flags_ingestao": parsed["flags"],
            "consistencia": consistencia,
        },
    )

    await step("concluida")
    return {
        "analysis_id": analysis_id,
        "project_id": project_id,
        "version": version,
        "resultados": [r for r in results],
    }