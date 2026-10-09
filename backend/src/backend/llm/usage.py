"""LLM usage meter: calls, tokens and time per role, recorded for the analysis running in this context."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import Field

from backend.api_schema import CamelModel


class RoleUsage(CamelModel):
    calls: int = 0
    failures: int = 0
    transport_retries: int = 0
    schema_retries: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_seconds: float = 0

    def add(self, other: "RoleUsage") -> None:
        for field in RoleUsage.model_fields:
            setattr(self, field, getattr(self, field) + getattr(other, field))
        self.llm_seconds = round(self.llm_seconds, 3)


class LLMUsage(CamelModel):
    roles: dict[str, RoleUsage] = Field(default_factory=dict)
    web_search_calls: int = 0
    web_fetch_calls: int = 0
    web_failures: int = 0

    def role(self, role: str) -> RoleUsage:
        return self.roles.setdefault(role, RoleUsage())

    def total(self) -> RoleUsage:
        total = RoleUsage()
        for usage in self.roles.values():
            total.add(usage)
        return total


# A mutable LLMUsage shared by every task the analysis spawns (gather copies the context, not the object).
_current: ContextVar[LLMUsage | None] = ContextVar("llm_usage", default=None)


@contextmanager
def meter_scope() -> Iterator[LLMUsage]:
    usage = LLMUsage()
    token = _current.set(usage)
    try:
        yield usage
    finally:
        _current.reset(token)


def current_usage() -> LLMUsage | None:
    return _current.get()
