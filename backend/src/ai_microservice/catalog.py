"""Loader + validação do catálogo rules.yaml (spec seção 4)."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class RuleMode(str, Enum):
    regra = "regra"
    llm = "llm"
    web = "web"
    design = "design"
    llm_regra = "regra+llm"
    llm_web = "web+llm"
    web_regra = "web+regra"
    regra_llm = "llm+regra"


class RuleStatus(str, Enum):
    aplicavel = "aplicavel"
    parcial = "parcial"
    na = "na"
    absorvida = "absorvida"


class Artifact(BaseModel):
    id: str
    nature: str


class Rule(BaseModel):
    id: str
    criterion: str
    block: str  # documento | web | transversal | shared
    mode: str
    what: str
    evidence: str = ""
    sources: list[str] = Field(default_factory=list)
    routing: list[str] = Field(default_factory=list)
    chk: str | None = None
    polarity_hint: str = "positive"
    scoring_role: str = "mean"  # mean | informativa | gate
    status: RuleStatus = RuleStatus.aplicavel
    status_reason: str | None = None
    absorbed_into: str | None = None
    prompt: str | None = None
    query_family: str | None = None

    @property
    def executes(self) -> bool:
        """Executa nesta iteração: aplicável e modo não-design."""
        return self.status == RuleStatus.aplicavel and self.mode != "design"

    @property
    def uses_llm(self) -> bool:
        return "llm" in self.mode

    @property
    def uses_web(self) -> bool:
        return "web" in self.mode


class Catalog(BaseModel):
    version: str
    artifacts: list[Artifact]
    rules: list[Rule]

    def by_id(self) -> dict[str, Rule]:
        return {r.id: r for r in self.rules}

    def rules_for_criterion(self, criterion: str) -> list[Rule]:
        return [r for r in self.rules if r.criterion == criterion and r.executes]


_CATALOG_CACHE: dict[Path, Catalog] = {}


def load_catalog(path: Path | None = None) -> Catalog:
    from ai_microservice.config import get_settings

    if path is None:
        path = get_settings().catalog_dir / "rules.yaml"
    path = Path(path)
    if path in _CATALOG_CACHE:
        return _CATALOG_CACHE[path]

    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = Catalog(
        version=str(raw["catalog_version"]),
        artifacts=[Artifact(**a) for a in raw["artifacts"]],
        rules=[Rule(**r) for r in raw["rules"]],
    )
    _validate(catalog)
    _CATALOG_CACHE[path] = catalog
    return catalog


def _validate(cat: Catalog) -> None:
    ids = [r.id for r in cat.rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"IDs duplicados no catálogo: {dupes}")

    artifact_ids = {a.id for a in cat.artifacts}
    for r in cat.rules:
        for rota in r.routing:
            base = rota.split("#")[0]
            if base not in artifact_ids:
                raise ValueError(f"{r.id}: routing para artefato inexistente '{rota}'")
        if r.status in (RuleStatus.na, RuleStatus.parcial, RuleStatus.absorvida) and not r.status_reason:
            raise ValueError(f"{r.id}: status {r.status} exige status_reason")
        if r.absorbed_into and r.absorbed_into not in ids and not r.absorbed_into.startswith("CHK"):
            raise ValueError(f"{r.id}: absorbed_into '{r.absorbed_into}' não existe no catálogo")
        if r.chk and r.chk not in ids:
            raise ValueError(f"{r.id}: chk '{r.chk}' não existe no catálogo")
        if r.executes and r.uses_llm and r.criterion not in ("transversal", "compartilhada") and not r.prompt:
            raise ValueError(f"{r.id}: regra {r.mode} ativa exige prompt")