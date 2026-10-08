from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.catalog.models import Catalog, CatalogRule, CriterionInfo, RuleDocument

CATALOG_PATH = Path(__file__).with_name("rules.yaml")


class CatalogError(ValueError):
    pass


def parse_catalog(raw: dict) -> Catalog:
    try:
        criteria = {key: CriterionInfo(id=key, **value) for key, value in (raw.get("criterios") or {}).items()}
        rules = [CatalogRule.model_validate(item) for item in raw.get("regras") or []]
        catalog = Catalog(
            versao=str(raw["versao"]),
            tipos_de_arquivo=raw.get("tipos_de_arquivo") or [],
            familias_web=raw.get("familias_web") or {},
            criteria=criteria,
            rules=rules,
        )
    except (ValidationError, KeyError) as error:
        raise CatalogError(f"invalid rule catalog: {error}") from error
    _validate(catalog)
    return catalog


def _validate(catalog: Catalog) -> None:
    seen: set[str] = set()
    for rule in catalog.rules:
        if rule.id in seen:
            raise CatalogError(f"duplicate rule id {rule.id}")
        seen.add(rule.id)
    for rule in catalog.rules:
        if rule.bloco != "transversal" and rule.criterio not in catalog.criteria:
            raise CatalogError(f"{rule.id}: unknown criterion {rule.criterio}")
        for target in rule.absorvida_em:
            if target not in seen:
                raise CatalogError(f"{rule.id}: absorbed into unknown rule {target}")
        if rule.status != "aplicavel" and not rule.motivo_status:
            raise CatalogError(f"{rule.id}: status {rule.status} needs motivo_status")
        if rule.needs_llm and not rule.prompt:
            raise CatalogError(f"{rule.id}: applicable LLM rule without prompt")


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    with path.open(encoding="utf-8") as file:
        return parse_catalog(yaml.safe_load(file))


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()


async def sync_catalog_to_db(catalog: Catalog) -> None:
    """Idempotent: replaces the stored rules with the current catalog version."""
    await RuleDocument.find_all().delete()
    await RuleDocument.insert_many(
        [RuleDocument(rule_id=rule.id, catalog_version=catalog.versao, rule=rule) for rule in catalog.rules]
    )
