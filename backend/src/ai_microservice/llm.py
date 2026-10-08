"""Client Ollama + AgentLoop (tool-calling) + retry/backoff — sem framework (~100 linhas)."""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
from typing import Any, Awaitable, Callable

from ollama import AsyncClient, ChatResponse

log = logging.getLogger("ai_microservice.llm")


class LLMError(RuntimeError):
    pass


def _default_client() -> AsyncClient:
    from ai_microservice.config import get_settings

    s = get_settings()
    if s.ollama_api_key:
        os.environ.setdefault("OLLAMA_API_KEY", s.ollama_api_key)
    return AsyncClient(host=s.ollama_base_url, timeout=300)


_client: AsyncClient | None = None
_client_loop: "asyncio.AbstractEventLoop | None" = None


def get_client() -> AsyncClient:
    """Client por event loop — recria quando o loop muda (ex.: asyncio.run sucessivos)."""
    global _client, _client_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if _client is None or _client_loop is not loop:
        if _client is not None:
            try:
                asyncio.ensure_future(_client.close())
            except Exception:
                pass
        _client = _default_client()
        _client_loop = loop
    return _client


def set_client(client: AsyncClient) -> None:
    global _client
    _client = client


async def chat(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    retries: int | None = None,
) -> ChatResponse:
    """chat com retry + backoff exponencial (rate limit do Ollama Cloud)."""
    from ai_microservice.config import get_settings

    max_retries = retries if retries is not None else get_settings().llm_max_retries
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "options": {"temperature": 0},  # reprodutibilidade (spec §2)
            }
            if tools:
                kwargs["tools"] = tools
            return await get_client().chat(**kwargs)
        except Exception as exc:  # rate limit / transient
            last_exc = exc
            wait = 2**attempt * 2
            log.warning("chat falhou (tentativa %d/%d): %s — aguardando %ss", attempt + 1, max_retries, exc, wait)
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
    raise LLMError(f"chat excedeu {max_retries} tentativas: {last_exc}") from last_exc


def _func_to_schema(fn: Callable) -> dict:
    """Converte função Python (docstring Google-style) em tool schema (o client ollama faz isso,
    mas garantimos formato estável aqui)."""
    name = fn.__name__
    doc = inspect.getdoc(fn) or ""
    desc = doc.split("\n\nArgs:")[0].strip()
    sig = inspect.signature(fn)
    properties: dict[str, dict] = {}
    required: list[str] = []
    type_map = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}
    for pname, p in sig.parameters.items():
        ann = p.annotation if p.annotation is not inspect.Parameter.empty else str
        tname = getattr(ann, "__name__", str(ann)).replace("Optional[", "").replace("]", "")
        js_t = type_map.get(tname, "string")
        prop: dict[str, Any] = {"type": js_t}
        # descrição do parâmetro do docstring (linha "pname: desc")
        for ln in doc.splitlines():
            m = ln.strip()
            if m.startswith(f"{pname}:"):
                prop["description"] = m[len(pname) + 1 :].strip()
                break
        properties[pname] = prop
        if p.default is inspect.Parameter.empty:
            required.append(pname)
    schema: dict[str, Any] = {"type": "function", "function": {"name": name, "description": desc}}
    if properties:
        schema["function"]["parameters"] = {"type": "object", "properties": properties, "required": required}
    return schema


class AgentLoop:
    """Loop próprio: mensagem → tool_calls → resultados → ... → resposta final.

    tools = funções Python síncronas ou assíncronas. O schema é derivado da
    assinatura/docstring. Temperatura 0 via options para reprodutibilidade.
    """

    def __init__(
        self,
        model: str,
        system: str,
        tools: list[Callable],
        max_rounds: int | None = None,
        max_output_chars: int = 8000,
    ):
        from ai_microservice.config import get_settings

        self.model = model
        self.system = system
        self.tools = list(tools)
        self.max_rounds = max_rounds or get_settings().agent_max_tool_rounds
        self.max_output_chars = max_output_chars
        self._by_name = {t.__name__: t for t in tools}
        self._schemas = [_func_to_schema(t) for t in tools]

    async def arun(self, prompt: str) -> str:
        messages: list[dict] = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": prompt},
        ]
        for _round in range(self.max_rounds):
            resp = await chat(self.model, messages, tools=self._schemas or None)
            msg = resp.message
            content = msg.content or ""
            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                return content.strip()
            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [tc.model_dump() for tc in tool_calls],
                }
            )
            for tc in tool_calls:
                fn = tc.function
                result = await self._call_tool(fn.name, fn.arguments)
                messages.append({"role": "tool", "name": fn.name, "content": result})
        # saiu por teto de rounds: pede resposta final sem tools
        resp = await chat(self.model, messages, tools=None)
        return (resp.message.content or "").strip()

    async def _call_tool(self, name: str, arguments: Any) -> str:
        fn = self._by_name.get(name)
        if fn is None:
            return f"ERRO: tool desconhecida {name}"
        try:
            if isinstance(arguments, str):
                args = json.loads(arguments)
            else:
                args = dict(arguments or {})
        except (json.JSONDecodeError, TypeError):
            return "ERRO: argumentos inválidos"
        try:
            out = fn(**args)
            if inspect.isawaitable(out):
                out = await out
        except Exception as exc:
            return f"ERRO na tool {name}: {type(exc).__name__}: {exc}"
        if not isinstance(out, str):
            out = json.dumps(out, ensure_ascii=False)
        return out[: self.max_output_chars]

    def run(self, prompt: str) -> str:
        """Interface síncrona (usada em scripts/testes)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(prompt))
        # já há loop rodando (API): roda em thread separada
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, self.arun(prompt)).result()