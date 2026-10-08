import asyncio
import logging
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from ollama import AsyncClient
from pydantic import BaseModel, ValidationError

from backend.config import LLMRole, Settings
from backend.llm.usage import LLMUsage, RoleUsage, current_usage

logger = logging.getLogger(__name__)

# web_search/web_fetch only exist on Ollama Cloud, even when chat runs on a local host.
OLLAMA_CLOUD_HOST = "https://ollama.com"
# Reproducibility (principle 11): every call runs at temperature 0. Not configurable on purpose.
DETERMINISTIC_OPTIONS = {"temperature": 0, "seed": 0}
RETRY_BACKOFF_S = 1.0

Message = Mapping[str, Any]


class LLMError(RuntimeError):
    pass


class WebSearchResult(BaseModel):
    title: str
    url: str
    content: str


class WebPage(BaseModel):
    url: str
    title: str
    content: str


class LLM(Protocol):
    """What the modules need from a language model; LLMClient in production, a fake in tests."""

    def model_for(self, role: LLMRole) -> str: ...

    async def chat(self, messages: Sequence[Message], role: LLMRole = "default") -> str: ...

    async def structured[T: BaseModel](
        self, messages: Sequence[Message], schema: type[T], role: LLMRole = "default"
    ) -> T: ...

    async def web_search(self, query: str, max_results: int = 5) -> list[WebSearchResult]: ...

    async def web_fetch(self, url: str) -> WebPage: ...


class LLMClient:
    """Single entry point to Ollama, shared by every module."""

    def __init__(
        self,
        settings: Settings,
        chat_client: AsyncClient | None = None,
        web_client: AsyncClient | None = None,
        retry_backoff_s: float = RETRY_BACKOFF_S,
    ) -> None:
        self.settings = settings
        self._retry_backoff_s = retry_backoff_s
        headers = {"Authorization": f"Bearer {settings.ollama_api_key}"} if settings.ollama_api_key else {}
        self._chat = chat_client or AsyncClient(
            host=settings.ollama_host, headers=headers, timeout=settings.ollama_timeout_s
        )
        self._web = web_client or AsyncClient(
            host=OLLAMA_CLOUD_HOST, headers=headers, timeout=settings.ollama_timeout_s
        )
        self._semaphore = asyncio.Semaphore(settings.ollama_max_concurrency)

    def model_for(self, role: LLMRole) -> str:
        return self.settings.model_for(role)

    async def _call(self, func, usage: RoleUsage | None = None, **kwargs):
        """Runs one Ollama call with the concurrency limit and simple retries on transport errors."""
        attempts = self.settings.ollama_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                async with self._semaphore:
                    started = time.monotonic()
                    response = await func(**kwargs)
                    if usage is not None:
                        usage.calls += 1
                        usage.llm_seconds = round(usage.llm_seconds + time.monotonic() - started, 3)
                        usage.prompt_tokens += getattr(response, "prompt_eval_count", None) or 0
                        usage.completion_tokens += getattr(response, "eval_count", None) or 0
                    return response
            except Exception as error:
                if attempt == attempts:
                    if usage is not None:
                        usage.failures += 1
                    raise LLMError(f"Ollama call failed after {attempts} attempt(s): {type(error).__name__}") from error
                if usage is not None:
                    usage.transport_retries += 1
                logger.warning("Ollama call failed (attempt %d/%d): %s", attempt, attempts, type(error).__name__)
                await asyncio.sleep(self._retry_backoff_s * attempt)

    @staticmethod
    def _role_usage(role: str) -> RoleUsage | None:
        meter = current_usage()
        return meter.role(role) if meter is not None else None

    async def chat(
        self,
        messages: Sequence[Message],
        role: LLMRole = "default",
        format: dict[str, Any] | None = None,
    ) -> str:
        response = await self._call(
            self._chat.chat,
            usage=self._role_usage(role),
            model=self.model_for(role),
            messages=list(messages),
            format=format,
            options=DETERMINISTIC_OPTIONS,
        )
        return response.message.content or ""

    async def structured[T: BaseModel](
        self, messages: Sequence[Message], schema: type[T], role: LLMRole = "default"
    ) -> T:
        """Chat validated against a Pydantic schema. Retries once, feeding the validation error back."""
        history = list(messages)
        json_schema = schema.model_json_schema()
        last_error: ValidationError | None = None
        for _ in range(2):
            content = await self.chat(history, role=role, format=json_schema)
            try:
                return schema.model_validate_json(content)
            except ValidationError as error:
                last_error = error
                if (usage := self._role_usage(role)) is not None:
                    usage.schema_retries += 1
                history += [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": f"The answer does not follow the requested JSON schema. Errors: {error}. "
                        "Answer again with valid JSON only.",
                    },
                ]
        raise LLMError(f"Invalid output for {schema.__name__}: {last_error}")

    async def web_search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        self._require_api_key()
        response = await self._web_call(self._web.web_search, "web_search_calls", query=query, max_results=max_results)
        return [
            WebSearchResult(title=r.title or "", url=r.url or "", content=r.content or "")
            for r in response.results
            if r.url
        ]

    async def web_fetch(self, url: str) -> WebPage:
        self._require_api_key()
        response = await self._web_call(self._web.web_fetch, "web_fetch_calls", url=url)
        return WebPage(url=url, title=response.title or "", content=response.content or "")

    async def _web_call(self, func, counter: str, **kwargs):
        meter: LLMUsage | None = current_usage()
        try:
            response = await self._call(func, **kwargs)
        except LLMError:
            if meter is not None:
                meter.web_failures += 1
            raise
        if meter is not None:
            setattr(meter, counter, getattr(meter, counter) + 1)
        return response

    def _require_api_key(self) -> None:
        if not self.settings.ollama_api_key:
            raise LLMError("OLLAMA_API_KEY is required for web_search/web_fetch")
