"""T6: queries sent to the internet carry no project codes, team names, internal codes or result numbers."""

import re
import unicodedata

from pydantic import BaseModel

MIN_SENSITIVE_TERM_LEN = 3
PROJECT_CODE_RE = re.compile(r"\bPRJ\d+(?:-[A-Z]+\d+)*\b", re.IGNORECASE)
INTERNAL_CODE_RE = re.compile(r"\b[A-Z]{2,}-\d+[A-Z]?\b")
# Numbers that look like results: decimals, percentages or 2+ digits. Single digits (HTTP 2) stay.
NUMBER_RE = re.compile(r"(?<![\w-])\d+(?:[.,]\d+)?%|(?<![\w-])\d+[.,]\d+(?![\w-])|(?<![\w-])\d{2,}(?![\w-])")


class SanitizedQuery(BaseModel):
    original: str
    sanitized: str
    removed: list[str]

    @property
    def changed(self) -> bool:
        return self.original.strip() != self.sanitized


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def find_sensitive_term(query: str, terms: list[str]) -> str | None:
    """First sensitive term present in the query (case and accent insensitive)."""
    normalized = _normalize(query)
    for term in terms:
        needle = _normalize(term).strip()
        if len(needle) >= MIN_SENSITIVE_TERM_LEN and re.search(rf"\b{re.escape(needle)}\b", normalized):
            return term
    return None


def _remove_term(query: str, term: str) -> str:
    """Removes a term ignoring case and accents: matches on the normalized text, cuts the original span."""
    normalized = _normalize(query)
    needle = _normalize(term).strip()
    match = re.search(rf"\b{re.escape(needle)}\b", normalized)
    if not match:
        return query
    # normalized index -> original index (normalizing one character may yield zero or several)
    mapping = []
    for index, char in enumerate(query):
        mapping.extend([index] * len(_normalize(char)))
    start, end = mapping[match.start()], mapping[match.end() - 1] + 1
    return query[:start] + " " + query[end:]


def sanitize_query(query: str, sensitive_terms: list[str]) -> SanitizedQuery:
    removed: list[str] = []
    text = query
    for pattern in (PROJECT_CODE_RE, INTERNAL_CODE_RE, NUMBER_RE):
        removed += [m.group(0) for m in pattern.finditer(text)]
        text = pattern.sub(" ", text)
    for term in sorted(sensitive_terms, key=len, reverse=True):
        while find_sensitive_term(text, [term]):
            removed.append(term)
            text = _remove_term(text, term)
    return SanitizedQuery(original=query, sanitized=" ".join(text.split()), removed=list(dict.fromkeys(removed)))
