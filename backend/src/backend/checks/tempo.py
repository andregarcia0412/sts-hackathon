"""CHK-TEMPO: the timeline from cronologia (SIS-D1, SIS-D2, CRI-D1, INC-D8): first and last date, the initial
document before the trials, progressive dates and more than one base year (T2)."""

from backend.checks.data import cell, rows
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject

INITIAL = "documento-inicial"


def check(canonical: CanonicalProject) -> CheckResult:
    events = [(cell(r, "data"), cell(r, "versao"), cell(r, "evento"), r.id) for r in rows(canonical, "cronologia")]
    dated = [e for e in events if e[0]]
    if not dated:
        return CheckResult(id="CHK-TEMPO", status="nao_aplicavel", notes=["sem cronologia datada"])
    dates = [d for d, *_ in dated]
    initial = [d for d, version, *_ in dated if version == INITIAL]
    later = [d for d, version, *_ in dated if version != INITIAL]
    initial_first = bool(initial) and all(min(initial) < d for d in later) if later else bool(initial)
    progressive = dates == sorted(dates)
    years = sorted({d[:4] for d in dates})
    facts = {
        "data_inicial": min(dates), "data_final": max(dates), "eventos": len(dated),
        "documento_inicial": min(initial) if initial else None,
        "documento_inicial_antes_dos_ensaios": initial_first,
        "datas_progressivas": progressive, "anos": years, "varios_anos_base": len(years) > 1,
    }
    ok = initial_first and progressive and len(years) == 1
    return CheckResult(id="CHK-TEMPO", status="ok" if ok else "alerta", facts=facts,
                       fragment_ids=[e[3] for e in dated])
