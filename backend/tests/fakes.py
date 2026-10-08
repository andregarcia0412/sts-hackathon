"""Test doubles for the LLM and search providers. No network in unit tests."""

from collections.abc import Callable
from datetime import date
from typing import Any

from pydantic import BaseModel

from backend.llm import LLMError, WebPage, WebSearchResult
from backend.llm.usage import current_usage
from backend.search.base import SearchHit

Handler = Callable[[list[dict[str, Any]]], Any] | BaseModel | dict | Exception


class FakeLLM:
    """Replaces LLMClient: answers by schema (or a chat handler) and records every call."""

    def __init__(self, handlers: dict[type[BaseModel], Handler] | None = None, chat: Handler | None = None) -> None:
        self.handlers = dict(handlers or {})
        self.chat_handler = chat
        self.calls: list[tuple[type[BaseModel] | None, str, list[dict[str, Any]]]] = []
        self.searches: list[str] = []
        self.search_results: list[WebSearchResult] = []
        self.pages: dict[str, WebPage] = {}

    def model_for(self, role: str) -> str:
        return f"fake-{role}"

    def calls_for(self, schema: type[BaseModel]) -> list[list[dict[str, Any]]]:
        return [messages for called, _, messages in self.calls if called is schema]

    @staticmethod
    def _resolve(handler: Handler, messages: list[dict[str, Any]]):
        if isinstance(handler, Exception):
            raise handler
        if callable(handler) and not isinstance(handler, BaseModel):
            result = handler(messages)
            if isinstance(result, Exception):
                raise result
            return result
        return handler

    @staticmethod
    def _meter(role: str) -> None:
        """Counts the call like LLMClient does, with fixed token numbers."""
        if (meter := current_usage()) is not None:
            usage = meter.role(role)
            usage.calls += 1
            usage.prompt_tokens += 10
            usage.completion_tokens += 2

    async def chat(self, messages, role="default") -> str:
        self.calls.append((None, role, list(messages)))
        self._meter(role)
        if self.chat_handler is None:
            raise LLMError("no chat handler")
        return self._resolve(self.chat_handler, list(messages))

    async def structured(self, messages, schema, role="default"):
        self.calls.append((schema, role, list(messages)))
        self._meter(role)
        if schema not in self.handlers:
            raise LLMError(f"FakeLLM has no handler for {schema.__name__}")
        result = self._resolve(self.handlers[schema], list(messages))
        return result if isinstance(result, schema) else schema.model_validate(result)

    async def web_search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        self.searches.append(query)
        return self.search_results[:max_results]

    async def web_fetch(self, url: str) -> WebPage:
        if url not in self.pages:
            raise LLMError(f"page not found: {url}")
        return self.pages[url]


class FakeSearchProvider:
    def __init__(self, name: str, hits: list[SearchHit] | None = None, error: Exception | None = None) -> None:
        self.name = name
        self.hits = hits or []
        self.error = error
        self.queries: list[str] = []

    async def search(self, query: str, before: date, limit: int) -> list[SearchHit]:
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.hits[:limit]

    async def enrich(self, hit: SearchHit) -> SearchHit:
        return hit


def user_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(m["content"] for m in messages if m["role"] == "user")
