"""Grounded justification (spec 09) — a SIGNAL, never a gate: a speculative explanation ("pode gerar risco")
without anything that points at the quoted text is marked `justificativa_especulativa`. The evidence stays and the
score does not change. Measured on 366 saved evidences: 1 match, a false positive ("pode ser recalculada"), which is
why "pode ser" is not a speculative modal here."""

import re

SPECULATIVE_RE = re.compile(r"\bpode(?:m)? (?:gerar|caracterizar|indicar|sugerir|haver)\b|\bpossivelmente\b|"
                            r"\btalvez\b|\bprovavelmente\b|\baparentemente\b", re.IGNORECASE)
ANCHORED_RE = re.compile(r"\bo trecho\b|\bo texto\b|\bo registro\b|\bo dossi[eê]\b|\bo documento\b|\bcita\b|"
                         r"\bdescreve\b|\bafirma\b|\bdeclara\b|\bdemonstra\b|\bporque\b|\bpois\b|\bindica que\b|"
                         r"\binforma\b|\bmostra\b|\bregistra\b", re.IGNORECASE)  # \b: "explicita" is not "cita"
FLAG = "justificativa_especulativa"


def speculative(explanation: str | None) -> bool:
    text = explanation or ""
    return bool(SPECULATIVE_RE.search(text)) and not ANCHORED_RE.search(text)


def flags_for(explanation: str | None, enabled: bool) -> list[str]:
    return [FLAG] if enabled and speculative(explanation) else []
