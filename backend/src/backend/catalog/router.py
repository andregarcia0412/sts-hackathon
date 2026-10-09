from fastapi import APIRouter, HTTPException, status

from backend.auth.dependencies import CurrentUser
from backend.catalog.models import CatalogRule, RuleDocument

router = APIRouter(prefix="/regras", tags=["catalog"])


@router.get("")
async def list_rules(user: CurrentUser, criterio: str | None = None, bloco: str | None = None) -> list[CatalogRule]:
    rules = [doc.rule for doc in await RuleDocument.find_all().to_list()]
    if criterio:
        rules = [rule for rule in rules if rule.criterio == criterio]
    if bloco:
        rules = [rule for rule in rules if rule.bloco == bloco]
    return rules


@router.get("/{rule_id}")
async def get_rule(rule_id: str, user: CurrentUser) -> CatalogRule:
    doc = await RuleDocument.find_one(RuleDocument.rule_id == rule_id.upper())
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return doc.rule
