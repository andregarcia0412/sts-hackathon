"""Smoke do loop de agente — REQUER OLLAMA_API_KEY no .env.

Marcado com `llm` para poder rodar seletivamente:
    .venv/bin/python -m pytest tests/test_agent_loop.py -m llm -v

Cobre o AgentLoop com uma tool FAKE (sem web), testando o ciclo
tool_call → resultado → resposta final em JSON.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
dotenv = BACKEND / ".env"
pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        not dotenv.exists() or not os.environ.get("OLLAMA_API_KEY") and not dotenv.exists(),
        reason="requer OLLAMA_API_KEY no backend/.env",
    ),
]


def _load_env():
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def test_agent_loop_com_tool_fake():
    _load_env()
    from ai_microservice.llm import AgentLoop
    from ai_microservice.config import get_settings

    settings = get_settings()

    calls = []

    def tool_fake(termo: str) -> str:
        """Retorna o fragmento que contém o termo.

        Args:
            termo: termo a buscar.
        """
        calls.append(termo)
        return "Texto do fragmento: Configurar deduplicação por (operação, versão)."

    loop = AgentLoop(
        model=settings.model_analyst,
        system="Você é um assistente de teste. Use a tool buscar para achar o texto e responda em JSON com o campo quote.",
        tools=[tool_fake],
    )
    result = loop.run("Busque 'deduplicação' e devolva o quote literal em JSON {\"quote\": ...}")
    assert "deduplicação" in result.lower()
    assert calls, "o agente deveria ter chamado a tool"


def test_agent_loop_llm_somente_extrai_rotulo():
    _load_env()
    from ai_microservice.llm import AgentLoop
    from ai_microservice.config import get_settings

    settings = get_settings()
    loop = AgentLoop(
        model=settings.model_extractor,
        system="Você só rotula conteúdo. Responda em JSON {\"tipo\": \"...\", \"resumo\": \"...\"}.",
        tools=[],
    )
    out = loop.run(
        "Conteúdo: '# PRJ01 — Método e referência\\n\\nDocumento sintético. Data de corte: 2025-04-07.' "
        "Rotule o tipo deste documento."
    )
    import json as _json
    import re as _re

    m = _re.search(r"\{.*\}", out, _re.S)
    assert m, f"resposta sem JSON: {out[:200]}"
    data = _json.loads(m.group(0))
    assert {"tipo", "resumo"} <= set(data.keys())
    # o rótulo menciona o conteúdo sem reescrever: menciona método/identificação
    blob = " ".join(str(v) for v in data.values()).lower()
    assert any(k in blob for k in ("metodo", "método", "identificação", "identificacao", "cabeçalho"))