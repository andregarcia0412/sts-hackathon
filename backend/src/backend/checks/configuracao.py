"""CHK-CONFIG: does the prior reference already provide the function? (NOV-D4, NOV-D10, CRI-D5, INC-D5)

Reads metodo §1 (prior reference) and §2 (mechanism): reference type, configuration verbs, "faixa já admitida",
"nenhum algoritmo modificado". A fact for the agents and the judge; it never forces a state by itself."""

import re

from backend.checks.data import method_section
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject

REFERENCE_TYPES = (
    ("manual", re.compile(r"\bmanua(?:l|is)\b", re.I)),
    ("catálogo", re.compile(r"\bcat[áa]logos?\b", re.I)),
    ("dicionário", re.compile(r"\bdicion[áa]rios?\b", re.I)),
    ("produto contratado", re.compile(r"\bcontratad[oa]s?\b|\bproduto\b|\bplataforma\b|\bfornecedor\b", re.I)),
)
CONFIG_VERBS = ("configurar", "configuração", "configurado", "ativar", "ativação", "cadastrar", "cadastro", "mapear",
                "mapeamento", "ajustar", "ajuste", "parametrizar", "habilitar", "customiz", "aplicar receita")
ADMITTED_RE = re.compile(r"(?:faixa|intervalo)[^.]{0,60}?j[áa] admitid[oa]|j[áa] (?:suportad|admitid)[oa]", re.I)
UNCHANGED_RE = re.compile(r"nenhum algoritmo[^.]{0,40}?(?:foi )?(?:modificado|alterado)|sem alterar o algoritmo", re.I)


def check(canonical: CanonicalProject) -> CheckResult:
    reference, mechanism = method_section(canonical, "1"), method_section(canonical, "2")
    if reference is None and mechanism is None:
        return CheckResult(id="CHK-CONFIG", status="nao_aplicavel", notes=["método sem §1/§2"])
    ref_text = reference.text if reference else ""
    mech_text = mechanism.text if mechanism else ""
    kind = next((name for name, pattern in REFERENCE_TYPES if pattern.search(ref_text)), None)
    lowered = mech_text.lower()
    verbs = [verb for verb in CONFIG_VERBS if verb in lowered]
    admitted = bool(ADMITTED_RE.search(mech_text) or ADMITTED_RE.search(ref_text))
    unchanged = bool(UNCHANGED_RE.search(mech_text) or UNCHANGED_RE.search(ref_text))
    provided = bool(kind and verbs) or admitted or unchanged
    return CheckResult(
        id="CHK-CONFIG", status="alerta" if provided else "ok",
        facts={"tipo_referencia_anterior": kind, "verbos_de_configuracao": verbs,
               "faixa_ja_admitida": admitted, "algoritmo_nao_modificado": unchanged,
               "indica_funcao_ja_fornecida": provided},
        fragment_ids=[f.id for f in (reference, mechanism) if f],
        notes=["indício para a leitura das regras; não força o estado sem evidência citada"],
    )
