"""CHK-ESCOPO: what was declared but not executed (REP-D7, NOV-D11): `*_executado: false` flags in the
configuration and the declared limit of the conclusion (metodo §6) and continuity (§7)."""

from backend.checks.data import config_fragment_id, configuration, method_section
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject


def _not_executed(value, path: str) -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key.endswith("_executado") and item is False:
                found.append(child)
            found += _not_executed(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += _not_executed(item, f"{path}[{index}]")
    return found


def check(canonical: CanonicalProject) -> CheckResult:
    config = configuration(canonical)
    flags = _not_executed(config, "")
    limit, continuity = method_section(canonical, "6"), method_section(canonical, "7")
    fragment_ids = [i for i in {config_fragment_id(canonical, flag.split(".")[0].split("[")[0]) for flag in flags} if i]
    fragment_ids += [f.id for f in (limit, continuity) if f]
    return CheckResult(
        id="CHK-ESCOPO", status="alerta" if flags else "ok",
        facts={"nao_executados": flags, "limite_declarado": limit.text if limit else None,
               "continuidade": continuity.text if continuity else None},
        fragment_ids=fragment_ids,
        notes=["limite excluído desde o início não gera ressalva; hipótese da própria pretensão não ensaiada gera"],
    )
