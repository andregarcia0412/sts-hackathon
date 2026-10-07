from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from ai_microservice.llm import WebPage, WebSearchResult

Handler = Callable[[list[dict[str, Any]]], BaseModel]


class FakeLLM:
    """Substitui o LLMClient: devolve respostas por schema e registra as chamadas."""

    def __init__(self, handlers: dict[type[BaseModel], Handler] | None = None) -> None:
        self.handlers = handlers or {}
        self.calls: list[tuple[type[BaseModel], list[dict[str, Any]]]] = []
        self.searches: list[str] = []
        self.search_results: list[WebSearchResult] = []
        self.pages: dict[str, WebPage] = {}

    def model_for(self, role: str) -> str:
        return f"fake-{role}"

    async def structured(self, messages, schema, role="default"):
        self.calls.append((schema, list(messages)))
        return self.handlers[schema](list(messages))

    async def web_search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        self.searches.append(query)
        return self.search_results[:max_results]

    async def web_fetch(self, url: str) -> WebPage:
        return self.pages[url]
