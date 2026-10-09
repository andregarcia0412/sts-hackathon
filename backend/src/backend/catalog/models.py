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
    forca_coluna: Literal["negativa"] | None = None  # state gate: predominant negative evidence forces the column
    requer_gate: list[str] = Field(default_factory=list)  # acts only if one of these gates fired (cross-criteria)
    fonte_de_referencia: bool = False  # its negative sources are the prior reference (consistency between criteria)

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


DEFAULT_OPTIONS = ["sim", "nao", "sem_registro"]
NO_RECORD = "sem_registro"


class Question(BaseModel):
    """A closed question of the judge questionnaire (catalog/questionario.yaml)."""

    id: str
    texto: str
    opcoes: list[str] = Field(default_factory=lambda: list(DEFAULT_OPTIONS))
    descricao_opcoes: dict[str, str] = Field(default_factory=dict)
    regras: list[str] = Field(default_factory=list)
    exige_registro_numerico: bool = False  # "sim" needs numeric evidence (medicoes/resultados) in the criterion
    sim_exige_documento: bool = False  # "sim" must cite package evidence: the web complements, never decides alone
    explicacao: str = ""  # the handbook pitfall that applies to this question


class DecisionLine(BaseModel):
    """`quando`: question → accepted answer(s); `senao`: matches anything. The first matching line wins."""

    quando: dict[str, str | list[str]] = Field(default_factory=dict)
    senao: bool = False
    estado: str

    def accepted(self, question_id: str) -> list[str]:
        value = self.quando[question_id]
        return [value] if isinstance(value, str) else list(value)

    def matches(self, answers: dict[str, str]) -> bool:
        return self.senao or all(answers.get(q, NO_RECORD) in self.accepted(q) for q in self.quando)

    def label(self) -> str:
        if self.senao:
            return "senão"
        return ", ".join(f"{q} = {' ou '.join(self.accepted(q))}" for q in self.quando)


class Questionnaire(BaseModel):
    perguntas: dict[CriterionId, list[Question]]
    decisao: dict[CriterionId, list[DecisionLine]]
    travas: dict[str, dict[str, str]] = Field(default_factory=dict)  # state gate rule → {question: locked answer}

    def question(self, criterion: str, question_id: str) -> Question | None:
        return next((q for q in self.perguntas.get(criterion, []) if q.id == question_id), None)


class Catalog(BaseModel):
    versao: str
    tipos_de_arquivo: list[str]
    familias_web: dict[str, str] = Field(default_factory=dict)
    criteria: dict[CriterionId, CriterionInfo]
    rules: list[CatalogRule]
    questionnaire: Questionnaire | None = None

    def get(self, rule_id: str) -> CatalogRule | None:
        return next((rule for rule in self.rules if rule.id == rule_id), None)

    @property
    def file_types(self) -> list[str]:
        return self.tipos_de_arquivo

    def executable_rules(self) -> list[CatalogRule]:
        return [rule for rule in self.rules if rule.executavel]

    def rules_for(self, criterion: str, block: Block) -> list[CatalogRule]:
        return [r for r in self.executable_rules() if r.criterio == criterion and r.bloco == block]

    def state_gates(self, criterion: str) -> list[CatalogRule]:
        """Rules that force the negative column of the criterion state (catalog data, not a dict in code)."""
        return [r for r in self.rules if r.criterio == criterion and r.forca_coluna and r.executavel]

    def reference_rules(self) -> list[CatalogRule]:
        return [r for r in self.rules if r.fonte_de_referencia]

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
