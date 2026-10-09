"""CHK-VERSOES: versions in cronologia × medicoes × configuracao (SIS-D12, CRI-D8): a claimed version without a
trial, and key parameters left null."""

from backend.checks.data import cell, config_fragment_id, configuration, rows
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject

NOT_EXECUTIONS = {"documento-inicial", "protocolo-r1", "revisao-final"}


def _nulls(value, prefix: str = "") -> list[str]:
    if value is None:
        return [prefix or "(raiz)"]
    if isinstance(value, dict):
        return [n for k, v in value.items() for n in _nulls(v, f"{prefix}.{k}" if prefix else k)]
    return []


def check(canonical: CanonicalProject) -> CheckResult:
    config = configuration(canonical)
    timeline = {cell(r, "versao") for r in rows(canonical, "cronologia")} - {None} - NOT_EXECUTIONS
    measured = {cell(r, "versao") for r in rows(canonical, "medicoes")} - {None}
    registered = {v for v in config.get("versoes_registradas") or [] if isinstance(v, str)}
    claimed = timeline | registered
    if not claimed and not measured:
        return CheckResult(id="CHK-VERSOES", status="nao_aplicavel", notes=["sem versões registradas"])
    without_trial = sorted(claimed - measured)
    null_parameters = _nulls(config.get("parametros"), "parametros") if "parametros" in config else []
    trials: dict[str, list[str]] = {}
    for r in rows(canonical, "medicoes"):
        if (version := cell(r, "versao")) and (trial := cell(r, "ensaio_id")) and trial not in trials.get(version, []):
            trials.setdefault(version, []).append(trial)
    fragment_ids = [i for i in (config_fragment_id(canonical, "versoes_registradas"),
                                config_fragment_id(canonical, "parametros")) if i]
    fragment_ids += [r.id for r in rows(canonical, "cronologia")]
    return CheckResult(
        id="CHK-VERSOES", status="alerta" if without_trial or null_parameters else "ok",
        facts={"versoes_alegadas": sorted(claimed), "versoes_com_medicao": sorted(measured),
               "versoes_sem_ensaio": without_trial, "parametros_nulos": null_parameters,
               "ensaios_por_versao": trials},
        fragment_ids=fragment_ids,
    )
