"""CHK-DIVERG candidates become recorded divergences (principle 6), so a planted numeric divergence is never lost
even when the document sub-agent misses it. Never duplicates one the sub-agent already wrote."""

import re

from backend.checks.models import ChecksReport
from backend.criteria.schemas import CriterionResult, Divergence
from backend.extraction.schema import CanonicalProject

CRITERION = "REP"  # numbers recomputable from the primary record (REP-D2/D9)


def check_divergences(checks: ChecksReport) -> list[Divergence]:
    result = checks.get("CHK-DIVERG")
    if result is None or result.status != "alerta":
        return []
    return [Divergence(criterion=CRITERION, testimony_fragment_id=c["depoimento_fragmento"],
                       testimony_quote=c["depoimento_trecho"], record_fragment_id=c["registro_fragmento"],
                       record_alias=c["registro_alias"], record_quote=c["registro_trecho"], statement=c["frase"])
            for c in result.facts.get("divergencias", [])]


def add_check_divergences(results: dict[str, CriterionResult], canonical: CanonicalProject,
                          checks: ChecksReport) -> int:
    known = {(d.testimony_fragment_id, d.record_fragment_id) for r in results.values() for d in r.divergences}
    known_quotes = {_normal(d.testimony_quote) for r in results.values() for d in r.divergences}
    added = 0
    for divergence in check_divergences(checks):
        if (divergence.testimony_fragment_id, divergence.record_fragment_id) in known:
            continue
        if any(_same_sentence(_normal(divergence.testimony_quote), other) for other in known_quotes if other):
            continue
        results.setdefault(CRITERION, CriterionResult(criterion=CRITERION)).divergences.append(divergence)
        added += 1
    return added


def dedupe_divergences(results: dict[str, CriterionResult]) -> int:
    """Keeps one record per interview sentence across the criteria (the first: usually the sub-agent's).
    Returns how many repeated records were dropped from the copy (the source analysis is never written)."""
    seen: list[str] = []
    dropped = 0
    for result in results.values():
        kept = []
        for divergence in result.divergences:
            quote = _normal(divergence.testimony_quote)
            if any(_same_sentence(quote, other) for other in seen):
                dropped += 1
                continue
            seen.append(quote)
            kept.append(divergence)
        result.divergences = kept
    return dropped


def _normal(text: str) -> str:
    """The same sentence quoted with or without its final period or quotes is the same divergence."""
    return re.sub(r"\W+", " ", text.casefold()).strip()


def _same_sentence(a: str, b: str) -> bool:
    """Equal, or one is the other plus a few characters (a final period, quotes). A short fragment quoted by the
    sub-agent never suppresses a deterministic candidate: that would fail open the guarantee of the check."""
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    return shorter in longer and len(shorter) >= 0.9 * len(longer)
