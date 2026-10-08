"""Agente intérprete (gemma4:31b) — rotula cada arquivo → enriquece o manifest (spec 5.2).

A LLM só rotula, nunca reescreve o conteúdo.
"""
from __future__ import annotations

import asyncio
import json
import re

from ai_microservice.extraction.parsers import Fragment
from ai_microservice.llm import AgentLoop

_SYSTEM = """Você é o intérprete de pacotes de evidências de projetos de P&D (Lei do Bem).
Sua função é SOMENTE ROTULAR conteúdo — nunca reescrever, nunca resumir além do pedido.
Para o arquivo apresentado, responda em JSON válido (sem markdown, sem cercas de código):
{
  "tipo": "um de: dossie | registro_tecnico | entrevista | atividades | inventario | metodo | cronologia | medicoes | resultados | configuracao | observacoes | entradas | revisao_tecnica | desconhecido",
  "do_que_trata": "uma frase",
  "secoes_reconhecidas": ["lista de seções/títulos reconhecidos no arquivo"]
}
Baseie o rótulo no CONTEÚDO (títulos, cabeçalhos, chaves), não no nome do arquivo."""


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def enrich_manifest(fragments: list[Fragment], manifest: dict, model: str | None = None) -> dict:
    """Um rótulo por ARTEFATO (não por fragmento) — amostra é o fragmento mais longo do artefato."""
    from ai_microservice.config import get_settings

    model = model or get_settings().model_extractor
    by_artifact: dict[str, Fragment] = {}
    for f in fragments:
        cur = by_artifact.get(f.artifact)
        if cur is None or len(f.text) > len(cur.text):
            by_artifact[f.artifact] = f
    interpretations: dict[str, dict] = {}
    for artifact, frag in sorted(by_artifact.items()):
        loop = AgentLoop(
            model=model,
            system=_SYSTEM,
            tools=[],
            max_rounds=1,
        )
        try:
            raw = await loop.arun(
                f"ARQUIVO: {artifact}\n\nCONTEÚDO:\n{frag.text[:4000]}\n\nRotule este arquivo."
            )
            interpretations[artifact] = _extract_json(raw) or {}
        except Exception as exc:  # falha do intérprete não derruba a ingestão
            interpretations[artifact] = {
                "tipo": "desconhecido",
                "erro": f"{type(exc).__name__}: {exc}",
            }
    manifest = dict(manifest)
    manifest["interpretations"] = interpretations
    return manifest