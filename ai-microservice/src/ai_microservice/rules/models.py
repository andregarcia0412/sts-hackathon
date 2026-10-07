from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RuleStatus(StrEnum):
    ENQUADRA = "enquadra"
    NAO_ENQUADRA = "nao_enquadra"
    INCONCLUSIVO = "inconclusivo"


class Rule(BaseModel):
    """Regra verificável de um critério de Frascati (ID no formato `critério-fonte-número`, ex.: NOV-W3)."""

    id: str
    criterio: str
    titulo: str
    o_que_verificar: str
    evidencia_esperada: str
    fontes_normativas: list[str]
    # o que significa "enquadra" / "nao_enquadra" nesta regra (usado pelo evaluator llm)
    como_julgar: str | None = None
    # procedural = verificada pelo próprio pipeline (sem LLM); llm = julgada a partir das fontes recuperadas
    evaluator: Literal["procedural", "llm"]


class Evidence(BaseModel):
    fonte_id: str
    titulo: str
    url: str
    data_publicacao: str | None = None
    frente: str | None = None
    justificativa: str


class RuleVerdict(BaseModel):
    id: str
    titulo: str
    status: RuleStatus
    resumo: str
    evidencias: list[Evidence] = Field(default_factory=list)
