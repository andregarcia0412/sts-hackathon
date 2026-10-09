from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field

CriterionId = Literal["NOV", "CRI", "INC", "SIS", "REP"]
CRITERIA_ORDER: tuple[CriterionId, ...] = ("NOV", "CRI", "INC", "SIS", "REP")
Block = Literal["web", "doc", "transversal"]
Mode = Literal["llm", "procedural", "design", "regra"]
Role = Literal["media", "informativa", "gate"]
Status = Literal["aplicavel", "parcial", "na"]


class StateVocabulary(BaseModel):
    positivo: list[str]
    negativo: str
    indeterminado: str

    def all_states(self) -> list[str]:
        return [*self.positivo, self.negativo, self.indeterminado]


class CriterionInfo(BaseModel):
    id: CriterionId
    nome: str
    chave: str
    pergunta: str
    fonte_normativa: str
    estados: StateVocabulary


class CatalogRule(BaseModel):
    id: str
    criterio: CriterionId | None = None
    bloco: Block
    titulo: str
    o_que_verificar: str = ""
    evidencia: str = ""
    fontes_normativas: list[str] = Field(default_factory=list)
    modo: Mode = "llm"
    papel: Role = "media"
    status: Status = "aplicavel"
    motivo_status: str | None = None
    polaridade_especial: str | None = None
    somente_positiva: bool = False
    roteamento: list[str] = Field(default_factory=list)
    prompt: str | None = None
    explicacao_simples: str = ""
    absorvida_em: list[str] = Field(default_factory=list)
    aplicacao: str | None = None
    instrucao_prompt: str | None = None

    @property
    def executavel(self) -> bool:
        """Runs in the criterion pipeline (absorbed markers and transversal rules never do)."""
        return not self.absorvida_em and self.bloco != "transversal"

    @property
    def needs_llm(self) -> bool:
        return self.executavel and self.status == "aplicavel" and self.modo == "llm"

    @property
    def in_mean(self) -> bool:
        return self.papel != "informativa"


class Catalog(BaseModel):
    versao: str
    tipos_de_arquivo: list[str]
    familias_web: dict[str, str] = Field(default_factory=dict)
    criteria: dict[CriterionId, CriterionInfo]
    rules: list[CatalogRule]

    def get(self, rule_id: str) -> CatalogRule | None:
        return next((rule for rule in self.rules if rule.id == rule_id), None)

    @property
    def file_types(self) -> list[str]:
        return self.tipos_de_arquivo

    def executable_rules(self) -> list[CatalogRule]:
        return [rule for rule in self.rules if rule.executavel]

    def rules_for(self, criterion: str, block: Block) -> list[CatalogRule]:
        return [r for r in self.executable_rules() if r.criterio == criterion and r.bloco == block]

    def prompt_instructions(self) -> list[str]:
        """Transversal rules that become instructions in every document sub-agent prompt."""
        return [f"{r.id}: {r.instrucao_prompt}" for r in self.rules if r.bloco == "transversal" and r.instrucao_prompt]


class RuleDocument(Document):
    """Catalog loaded into Mongo on startup (one document per rule, tagged with the catalog version)."""

    rule_id: str
    catalog_version: str
    rule: CatalogRule

    class Settings:
        name = "rules"
