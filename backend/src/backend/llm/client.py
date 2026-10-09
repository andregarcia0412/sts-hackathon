import asyncio
import json
import logging
import re
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
# Some models answer ```json ... ``` or wrap the JSON in prose even with `format` set.
FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
SCHEMA_INSTRUCTION = (
    "Responda SOMENTE com um objeto JSON válido conforme o JSON Schema abaixo: use exatamente os nomes de "
    "campo do schema, preencha todos os campos obrigatórios e respeite os tipos. Sem markdown, sem texto fora "
    "do JSON.\nJSON Schema:\n{schema}"
)

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
        """Chat validated against a Pydantic schema.

        `format` alone is not enough: some models ignore it. The schema also goes in the prompt, fenced or
        wrapped JSON is unwrapped, and an invalid answer is retried with the failing fields and the
        expected field names (OLLAMA_SCHEMA_RETRIES times).
        """
        json_schema = schema.model_json_schema()
        history = _with_schema_instruction(list(messages), json_schema)
        last_error: ValidationError | None = None
        for _ in range(self.settings.ollama_schema_retries + 1):
            content = await self.chat(history, role=role, format=json_schema)
            try:
                return schema.model_validate_json(extract_json(content))
            except ValidationError as error:
                last_error = error
                if (usage := self._role_usage(role)) is not None:
                    usage.schema_retries += 1  # invalid answers
                history += [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": _schema_feedback(error, schema)},
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


def extract_json(content: str) -> str:
    """The JSON inside a ```json fence, or between the first '{' and the last '}' when wrapped in prose."""
    text = content.strip()
    if match := FENCE_RE.search(text):
        text = match.group(1).strip()
    if not text.startswith(("{", "[")) and "{" in text and "}" in text:
        text = text[text.index("{"): text.rindex("}") + 1]
    return text


def _with_schema_instruction(messages: list[Message], json_schema: dict[str, Any]) -> list[Message]:
    """Inserts the schema as a system message right after the leading system message(s)."""
    instruction = {"role": "system",
                   "content": SCHEMA_INSTRUCTION.format(schema=json.dumps(json_schema, ensure_ascii=False))}
    position = next((i for i, m in enumerate(messages) if m.get("role") != "system"), len(messages))
    return [*messages[:position], instruction, *messages[position:]]


def _fields_of(schema: type[BaseModel], loc: tuple) -> list[str]:
    """Field names expected at the object where the error happened (walks nested models and lists)."""
    model: Any = schema
    for part in loc[:-1]:
        if isinstance(part, int) or not (isinstance(model, type) and issubclass(model, BaseModel)):
            continue
        field = model.model_fields.get(part)
        if field is None:
            break
        annotation = field.annotation
        for candidate in (annotation, *getattr(annotation, "__args__", ())):
            inner = (candidate, *getattr(candidate, "__args__", ()))
            found = next((c for c in inner if isinstance(c, type) and issubclass(c, BaseModel)), None)
            if found is not None:
                model = found
                break
    return list(model.model_fields) if isinstance(model, type) and issubclass(model, BaseModel) else []


def _schema_feedback(error: ValidationError, schema: type[BaseModel]) -> str:
    problems = error.errors(include_url=False)
    if problems and problems[0]["type"] == "json_invalid":
        return ("The answer is not valid JSON (it does not follow the requested schema). "
                "Answer again with the JSON object only, without markdown fences or text around it.")
    lines = []
    for problem in problems[:12]:
        loc = tuple(problem["loc"])
        expected = _fields_of(schema, loc) if loc else []
        hint = f" (campos esperados neste objeto: {', '.join(expected)})" if expected else ""
        lines.append(f"- {'.'.join(str(p) for p in loc) or '(raiz)'}: {problem['msg']}{hint}")
    more = f"\n- ... e mais {len(problems) - 12} erro(s) do mesmo tipo" if len(problems) > 12 else ""
    return ("The answer does not follow the requested JSON schema. Fix these fields and answer again with the "
            "complete JSON only, using the exact field names of the schema:\n" + "\n".join(lines) + more)
