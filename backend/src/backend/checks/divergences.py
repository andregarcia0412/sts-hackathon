"""CHK-DIVERG candidates become recorded divergences (principle 6), so a planted numeric divergence is never lost
even when the document sub-agent misses it. Never duplicates one the sub-agent already wrote."""

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
    known_quotes = {d.testimony_quote.strip() for r in results.values() for d in r.divergences}
    added = 0
    for divergence in check_divergences(checks):
        if (divergence.testimony_fragment_id, divergence.record_fragment_id) in known:
            continue
        if divergence.testimony_quote.strip() in known_quotes:
            continue
        results.setdefault(CRITERION, CriterionResult(criterion=CRITERION)).divergences.append(divergence)
        added += 1
    return added
