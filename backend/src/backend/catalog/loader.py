from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.catalog.models import Catalog, CatalogRule, CriterionInfo, Questionnaire, RuleDocument

CATALOG_PATH = Path(__file__).with_name("rules.yaml")
QUESTIONNAIRE_PATH = Path(__file__).with_name("questionario.yaml")


class CatalogError(ValueError):
    pass


def parse_catalog(raw: dict, questionnaire: dict | None = None) -> Catalog:
    try:
        criteria = {key: CriterionInfo(id=key, **value) for key, value in (raw.get("criterios") or {}).items()}
        rules = [CatalogRule.model_validate(item) for item in raw.get("regras") or []]
        catalog = Catalog(
            versao=str(raw["versao"]),
            tipos_de_arquivo=raw.get("tipos_de_arquivo") or [],
            familias_web=raw.get("familias_web") or {},
            criteria=criteria,
            rules=rules,
            questionnaire=Questionnaire.model_validate(questionnaire) if questionnaire else None,
        )
    except (ValidationError, KeyError) as error:
        raise CatalogError(f"invalid rule catalog: {error}") from error
    _validate(catalog)
    if catalog.questionnaire:
        _validate_questionnaire(catalog)
    return catalog


def _validate_questionnaire(catalog: Catalog) -> None:
    q = catalog.questionnaire
    for criterion, questions in q.perguntas.items():
        vocabulary = catalog.criteria[criterion].estados.all_states()
        known = {question.id: question for question in questions}
        for question in questions:
            for rule_id in question.regras:
                if catalog.get(rule_id) is None:
                    raise CatalogError(f"questionnaire {question.id}: unknown rule {rule_id}")
        lines = q.decisao.get(criterion) or []
        if not lines or not lines[-1].senao:
            raise CatalogError(f"questionnaire {criterion}: the decision table must end with `senao`")
        for line in lines:
            if line.estado not in vocabulary:
                raise CatalogError(f"questionnaire {criterion}: state outside the vocabulary {line.estado!r}")
            for question_id in line.quando:
                if question_id not in known:
                    raise CatalogError(f"questionnaire {criterion}: unknown question {question_id}")
                options = set(known[question_id].opcoes) | {"sem_registro"}
                if bad := set(line.accepted(question_id)) - options:
                    raise CatalogError(f"questionnaire {question_id}: unknown option(s) {sorted(bad)}")


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


def load_catalog(path: Path = CATALOG_PATH, questionnaire_path: Path | None = QUESTIONNAIRE_PATH) -> Catalog:
    with path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    questionnaire = None
    if questionnaire_path is not None and questionnaire_path.is_file():
        with questionnaire_path.open(encoding="utf-8") as file:
            questionnaire = yaml.safe_load(file)
    return parse_catalog(raw, questionnaire)


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()


async def sync_catalog_to_db(catalog: Catalog) -> None:
    """Idempotent: replaces the stored rules with the current catalog version."""
    await RuleDocument.find_all().delete()
    await RuleDocument.insert_many(
        [RuleDocument(rule_id=rule.id, catalog_version=catalog.versao, rule=rule) for rule in catalog.rules]
    )
