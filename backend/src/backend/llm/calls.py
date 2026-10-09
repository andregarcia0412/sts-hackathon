"""Per-call log of the LLM (spec 07): which model got how many requests, at which stage, with what latency.

Only numbers — never the prompt or the answer (the project content already lives in the analysis; duplicating it
widens the leak surface). Calls accumulate in memory during the analysis and are written once at the end."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field

from backend.api_schema import CamelModel

CallKind = Literal["chat", "web_search", "web_fetch"]


class CallRecord(BaseModel):
    stage: str | None = None  # extracao, checagens, NOV…REP, grafo, parecer
    role: str | None = None
    model: str | None = None
    schema_name: str | None = None  # e.g. DocSubOut
    kind: CallKind = "chat"
    attempt: int = 1
    ok: bool = True
    error_type: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_s: float = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMCall(Document, CallRecord):
    analysis_id: str
    benchmark_id: str | None = None

    class Settings:
        name = "llm_calls"
        indexes = ["analysis_id", "benchmark_id"]


class ModelUsage(CamelModel):
    calls: int = 0
    failures: int = 0
    retries: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    durations_s: list[float] = Field(default_factory=list)  # successful calls, for p50/p95 across runs


class CallsSummary(CamelModel):
    """The call log aggregated for one analysis (saved with it; the benchmark reads only this)."""

    by_model: dict[str, ModelUsage] = Field(default_factory=dict)
    by_stage: dict[str, ModelUsage] = Field(default_factory=dict)
    by_model_role: dict[str, dict[str, int]] = Field(default_factory=dict)  # model → role → calls
    by_model_stage: dict[str, dict[str, int]] = Field(default_factory=dict)  # model → stage → calls


_stage: ContextVar[str | None] = ContextVar("llm_stage", default=None)
_calls: ContextVar[list[CallRecord] | None] = ContextVar("llm_calls", default=None)


@contextmanager
def stage_scope(name: str) -> Iterator[None]:
    token = _stage.set(name)
    try:
        yield
    finally:
        _stage.reset(token)


def set_stage(name: str) -> None:
    """For a whole task (a criterion of the runner): the gathered children inherit it."""
    _stage.set(name)


@contextmanager
def calls_scope() -> Iterator[list[CallRecord]]:
    calls: list[CallRecord] = []
    token = _calls.set(calls)
    try:
        yield calls
    finally:
        _calls.reset(token)


def record_call(**fields) -> None:
    if (calls := _calls.get()) is not None:
        calls.append(CallRecord(stage=_stage.get(), **fields))


def summarize(calls: list[CallRecord]) -> CallsSummary:
    summary = CallsSummary()
    for call in calls:
        model = call.model or "?"
        stage = call.stage or "?"
        for bucket in (summary.by_model.setdefault(model, ModelUsage()), summary.by_stage.setdefault(stage, ModelUsage())):
            if call.attempt > 1:
                bucket.retries += 1
            if not call.ok:
                bucket.failures += 1
                continue
            bucket.calls += 1
            bucket.prompt_tokens += call.prompt_tokens
            bucket.completion_tokens += call.completion_tokens
            bucket.durations_s.append(round(call.duration_s, 3))
        if call.ok:
            roles = summary.by_model_role.setdefault(model, {})
            roles[call.role or "?"] = roles.get(call.role or "?", 0) + 1
            stages = summary.by_model_stage.setdefault(model, {})
            stages[stage] = stages.get(stage, 0) + 1
    return summary


async def save_calls(analysis_id: str, benchmark_id: str | None, calls: list[CallRecord]) -> None:
    if calls:
        await LLMCall.insert_many([LLMCall(analysis_id=analysis_id, benchmark_id=benchmark_id, **c.model_dump())
                                   for c in calls])


def clock() -> float:
    return time.monotonic()
