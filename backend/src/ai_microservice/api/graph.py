"""GET /graph/{project_id} + GET /regras — leitura do grafo e do catálogo."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai_microservice.catalog import load_catalog
from ai_microservice.config import get_settings
from ai_microservice.graph.store import JSONFileGraphStore

router = APIRouter()


def _store() -> JSONFileGraphStore:
    s = get_settings()
    return JSONFileGraphStore(base_dir=s.graphs_dir)


@router.get("/graph/{project_id}")
async def get_graph(project_id: str):
    try:
        return _store().get_graph(project_id)
    except FileNotFoundError:
        raise HTTPException(404, f"sem grafo para {project_id}") from None


@router.get("/regras")
async def get_rules():
    cat = load_catalog()
    return {
        "catalog_version": cat.version,
        "rules": [
            {
                "id": r.id,
                "criterion": r.criterion,
                "block": r.block,
                "mode": r.mode,
                "what": r.what,
                "evidence": r.evidence,
                "sources": r.sources,
                "routing": r.routing,
                "status": r.status.value,
                "status_reason": r.status_reason,
                "absorbed_into": r.absorbed_into,
                "polarity_hint": r.polarity_hint,
                "scoring_role": r.scoring_role,
            }
            for r in cat.rules
        ],
    }


@router.get("/regras/{rule_id}")
async def get_rule(rule_id: str):
    cat = load_catalog()
    rule = cat.by_id().get(rule_id)
    if rule is None:
        raise HTTPException(404, f"regra {rule_id} não existe")
    return {
        "id": rule.id,
        "criterion": rule.criterion,
        "block": rule.block,
        "mode": rule.mode,
        "what": rule.what,
        "evidence": rule.evidence,
        "sources": rule.sources,
        "routing": rule.routing,
        "status": rule.status.value,
        "status_reason": rule.status_reason,
        "absorbed_into": rule.absorbed_into,
        "polarity_hint": rule.polarity_hint,
        "scoring_role": rule.scoring_role,
        "prompt": rule.prompt,
    }