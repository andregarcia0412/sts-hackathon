"""Gates de evidência: citação literal (V9) + fundamentação (V9.1).

Gate 1 (citação): o quote precisa existir literalmente na fonte.
Compara com colapso de espaços/quebras de linha (o LLM pode reflowar
whitespace ao copiar) — mas sem perdoar paráfrase: o texto tem de ser
o mesmo caractere a caractere fora do whitespace.

Gate 2 (fundamentação, V9.1): justificativa especulativa SEM ancoragem no
trecho é rejeitada — o furo do PRJ01 v1 foi INC-D1 sustentada por "pode gerar
comportamento inesperado" sem nenhum registro que mostre o risco.
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")

# modal especulativo: afirma possibilidade sem declarar origem no registro
_ESPECULATIVO_RE = re.compile(r"pode (?:gerar|caracterizar|indicar|sugerir|ser|haver)|possivelmente|talvez|provavelmente|aparentemente", re.I)
# ancoragem: justificativa que aponta o trecho como origem da afirmação
_ANCORAGEM_RE = re.compile(
    r"o trecho|o texto|o registro|o dossi[eê]|o documento|cita|descreve|afirma|"
    r"declara|demonstra|porque|pois|indica que|informa|mostra|registra",
    re.I,
)


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().lower()


def quote_in_source(quote: str | None, source: str | None) -> bool:
    """True se o quote existe literalmente (substring) na fonte."""
    if not quote or not quote.strip():
        return False
    if not source:
        return False
    return _norm(quote) in _norm(source)


def valida_justificativa(justificativa: str | None) -> tuple[bool, str]:
    """Gate de fundamentação (V9.1).

    Rejeita: vazia/curta (<6 palavras) e especulativa sem ancoragem —
    "pode gerar X" sem nenhum conector que aponte o trecho como base.
    """
    if not justificativa or not justificativa.strip():
        return False, "justificativa ausente"
    j = justificativa.strip()
    if len(j.split()) < 6:
        return False, "justificativa insuficiente (<6 palavras)"
    tem_modal = bool(_ESPECULATIVO_RE.search(j))
    tem_ancora = bool(_ANCORAGEM_RE.search(j))
    if tem_modal and not tem_ancora:
        return False, (
            "especulativa sem ancoragem no quote: afirma possibilidade ('pode …') "
            "sem apontar o trecho/registro de onde isso decorre"
        )
    return True, ""