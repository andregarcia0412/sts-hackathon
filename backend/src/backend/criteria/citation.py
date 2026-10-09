"""Citation gate (principle 2): a quote counts only if it exists verbatim in its source."""

import unicodedata

WRAPPERS = "\"'“”‘’«»"
ELLIPSES = ("...", "…")


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _trim(quote: str) -> str:
    text = normalize(quote).strip(WRAPPERS + " ")
    changed = True
    while changed:
        changed = False
        for ellipsis in ELLIPSES:
            if text.startswith(ellipsis):
                text, changed = text[len(ellipsis):].strip(WRAPPERS + " "), True
            if text.endswith(ellipsis):
                text, changed = text[: -len(ellipsis)].strip(WRAPPERS + " "), True
    return text


def quote_in(quote: str, source_text: str) -> bool:
    trimmed = _trim(quote)
    return bool(trimmed) and trimmed in normalize(source_text)


def clean_quote(quote: str) -> str:
    return _trim(quote)
