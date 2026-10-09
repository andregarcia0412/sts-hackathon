"""One answer of the judge questionnaire, as recorded in the criterion state (spec 12)."""

from typing import Literal

from pydantic import BaseModel, Field

NO_RECORD = "sem_registro"


class Answer(BaseModel):
    pergunta: str  # "N1"
    resposta: str  # one of the question options
    evidencias: list[str] = Field(default_factory=list)  # ev-... ids of this criterion
    explicacao: str = ""
    o_que_falta: str | None = None  # required with sem_registro: the missing link
    evidencias_a_solicitar: list[str] = Field(default_factory=list)
    origem: Literal["juiz", "gate"] = "juiz"  # gate = filled or overridden by a gate in code
    status: Literal["ok", "nao_fundamentada"] = "ok"  # nao_fundamentada = no valid evidence after the new attempt

    @property
    def effective(self) -> str:
        """What the decision table reads: an answer without evidence counts as no record."""
        return NO_RECORD if self.status == "nao_fundamentada" else self.resposta
