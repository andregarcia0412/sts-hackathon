"""Gate de citação: o quote precisa existir literalmente na fonte.

Compara com colapso de espaços/quebras de linha (o LLM pode reflowar
whitespace ao copiar) — mas sem perdoar paráfrase: o texto tem de ser
o mesmo caractere a caractere fora do whitespace.
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().lower()


def quote_in_source(quote: str | None, source: str | None) -> bool:
    """True se o quote existe literalmente (substring) na fonte."""
    if not quote or not quote.strip():
        return False
    if not source:
        return False
    return _norm(quote) in _norm(source)