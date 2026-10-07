import asyncio
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from ollama import AsyncClient
from pydantic import BaseModel, ValidationError

from ai_microservice.config import LLMRole, Settings, get_settings

# web_search/web_fetch só existem no Ollama Cloud, mesmo quando o chat roda local.
OLLAMA_CLOUD_HOST = "https://ollama.com"

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


class LLMClient:
    """Ponto único de acesso ao Ollama, compartilhado por todos os módulos do serviço."""

    def __init__(
        self,
        settings: Settings,
        chat_client: AsyncClient | None = None,
        web_client: AsyncClient | None = None,
    ) -> None:
        self.settings = settings
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

    async def chat(
        self,
        messages: Sequence[Message],
        role: LLMRole = "default",
        format: dict[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> str:
        async with self._semaphore:
            response = await self._chat.chat(
                model=self.model_for(role), messages=list(messages), format=format, options=options
            )
        return response.message.content or ""

    async def structured[T: BaseModel](
        self, messages: Sequence[Message], schema: type[T], role: LLMRole = "default"
    ) -> T:
        """Chat com saída validada contra um schema Pydantic. Tenta de novo uma vez, devolvendo o erro à LLM."""
        history = list(messages)
        json_schema = schema.model_json_schema()
        last_error: ValidationError | None = None
        for _ in range(2):
            content = await self.chat(history, role=role, format=json_schema, options={"temperature": 0})
            try:
                return schema.model_validate_json(content)
            except ValidationError as error:
                last_error = error
                history += [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": f"A resposta não segue o schema JSON pedido. Erros: {error}. "
                        "Responda de novo somente com o JSON válido.",
                    },
                ]
        raise LLMError(f"Saída inválida para {schema.__name__}: {last_error}")

    async def web_search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        self._require_api_key()
        async with self._semaphore:
            response = await self._web.web_search(query, max_results=max_results)
        return [
            WebSearchResult(title=r.title or "", url=r.url or "", content=r.content or "")
            for r in response.results
            if r.url
        ]

    async def web_fetch(self, url: str) -> WebPage:
        self._require_api_key()
        async with self._semaphore:
            response = await self._web.web_fetch(url)
        return WebPage(url=url, title=response.title or "", content=response.content or "")

    def _require_api_key(self) -> None:
        if not self.settings.ollama_api_key:
            raise LLMError("OLLAMA_API_KEY é obrigatória para web_search/web_fetch")


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())
