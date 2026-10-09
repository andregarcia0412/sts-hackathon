from typing import Any, Literal

from pydantic import BaseModel, Field

CHECKS_VERSION = "1.0"
CheckStatus = Literal["ok", "alerta", "nao_aplicavel", "falhou"]  # falhou = exception: never becomes a zero


class CheckResult(BaseModel):
    id: str  # "CHK-RECALC"
    status: CheckStatus
    facts: dict[str, Any] = Field(default_factory=dict)  # what the check found (numbers copied from the record)
    fragment_ids: list[str] = Field(default_factory=list)  # where it came from, for citation
    notes: list[str] = Field(default_factory=list)


class ChecksReport(BaseModel):
    version: str = CHECKS_VERSION
    results: dict[str, CheckResult] = Field(default_factory=dict)

    def get(self, check_id: str) -> CheckResult | None:
        return self.results.get(check_id)
