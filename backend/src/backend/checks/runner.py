"""Runs every check once per project, before the criterion agents. Pure functions: zero tokens, no I/O.

A check that raises becomes `falhou` (never a zero) and the analysis goes on."""

import json

from backend.checks import (
    configuracao,
    diverg,
    escopo,
    falhas,
    pergunta,
    recalc,
    tempo,
    versoes,
)
from backend.checks.models import CHECKS_VERSION, CheckResult, ChecksReport
from backend.errors import safe_error_message
from backend.extraction.schema import CanonicalProject, Fragment

CHECKS = {
    "CHK-RECALC": recalc.check,
    "CHK-TEMPO": tempo.check,
    "CHK-VERSOES": versoes.check,
    "CHK-FALHAS": falhas.check,
    "CHK-CONFIG": configuracao.check,
    "CHK-ESCOPO": escopo.check,
    "CHK-DIVERG": diverg.check,
    "CHK-PERGUNTA": pergunta.check,
}
CHECK_FILE = "checagens"


def run_checks(canonical: CanonicalProject) -> ChecksReport:
    report = ChecksReport(version=CHECKS_VERSION)
    for check_id, check in CHECKS.items():
        try:
            report.results[check_id] = check(canonical)
        except Exception as error:  # defensive: one broken check must not take the analysis down
            report.results[check_id] = CheckResult(id=check_id, status="falhou", notes=[safe_error_message(error)])
    return report


def check_text(result: CheckResult) -> str:
    """The canonical JSON of a check: the citable text (sorted, never truncated)."""
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=1)


def check_fragments(canonical: CanonicalProject, report: ChecksReport) -> list[Fragment]:
    """Each check as a citable fragment of nature `derivado` (it is computed, never a primary record)."""
    return [Fragment(id=f"{canonical.project_code}-{check_id}", alias=f"{CHECK_FILE}#{check_id}", file=CHECK_FILE,
                     file_type="checagem", anchor=check_id, text=check_text(result), nature="derivado")
            for check_id, result in report.results.items() if result.status != "nao_aplicavel"]


def with_check_fragments(canonical: CanonicalProject, report: ChecksReport) -> CanonicalProject:
    kept = [f for f in canonical.fragments if f.file_type != "checagem"]
    return canonical.model_copy(update={"fragments": kept + check_fragments(canonical, report)})
