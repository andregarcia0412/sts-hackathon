"""Reading the canonical project for the checks: by file type (identified by content), never by file name."""

import json
import math
import re
from typing import Any

from backend.extraction.schema import CanonicalProject, Fragment

NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def rows(canonical: CanonicalProject, file_type: str) -> list[Fragment]:
    return [f for f in canonical.fragments_of(file_type) if f.data]


def cell(fragment: Fragment, column: str) -> str | None:
    value = (fragment.data or {}).get(column)
    return value.strip() if isinstance(value, str) and value.strip() else None  # empty ≠ zero


def number(value: Any) -> float | None:
    """A recorded number as float; empty, missing or non-numeric is None (never 0)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(",", ".")  # records are machine-written decimals
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def prose_number(token: str) -> float | None:
    """A number written in Portuguese prose (interviews): "1.152" is a thousand separator, "2,8" a decimal comma."""
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", token):
        token = token.replace(".", "").replace(",", ".")
    return number(token)


def same(a: float | None, b: float | None) -> bool | None:
    """None when either side is empty: an empty cell is not a mismatch."""
    if a is None or b is None:
        return None
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)


def configuration(canonical: CanonicalProject) -> dict[str, Any]:
    """The configuration JSON, rebuilt from its top-level fragments (one per key)."""
    config: dict[str, Any] = {}
    for fragment in canonical.fragments_of("configuracao"):
        try:
            config[fragment.anchor] = json.loads(fragment.text)
        except (json.JSONDecodeError, TypeError):
            config[fragment.anchor] = fragment.text
    return config


def config_fragment_id(canonical: CanonicalProject, key: str) -> str | None:
    return next((f.id for f in canonical.fragments_of("configuracao", key)), None)


def method_section(canonical: CanonicalProject, section: str) -> Fragment | None:
    return next(iter(canonical.fragments_of("metodo", section)), None)
