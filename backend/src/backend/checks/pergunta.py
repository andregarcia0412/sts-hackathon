"""CHK-PERGUNTA: the registered questions (`Pergunta:` in the activities) that already name the known solution
("aplicar a técnica conhecida", "integrar ao cofre contratado") — routine, not technological uncertainty (INC-D2)."""

import re

from backend.checks.data import cell, rows
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject

QUESTION_RE = re.compile(r"Pergunta:\s*(.+)", re.IGNORECASE | re.DOTALL)
MARKER_RE = re.compile(r"\b(conhecid[oa]s?|existentes?|contratad[oa]s?|dispon[íi]ve(?:l|is)|admitid[oa]s?)\b",
                       re.IGNORECASE)


def check(canonical: CanonicalProject) -> CheckResult:
    seen: dict[str, dict] = {}
    for activity in rows(canonical, "atividades"):
        for column in ("resultado_ou_saida", "descricao"):
            text = cell(activity, column)
            if not text or not (match := QUESTION_RE.search(text)):
                continue
            question = " ".join(match.group(1).split())
            key = question.lower()
            if key in seen:  # the same activity in the CSV and the XLSX
                continue
            marker = MARKER_RE.search(question)
            seen[key] = {"pergunta": question, "marcador": marker.group(1) if marker else None,
                         "aplica_solucao_conhecida": bool(marker), "fragmento": activity.id}
    if not seen:
        return CheckResult(id="CHK-PERGUNTA", status="nao_aplicavel", notes=["nenhuma 'Pergunta:' nas atividades"])
    questions = list(seen.values())
    known = any(q["aplica_solucao_conhecida"] for q in questions)
    return CheckResult(id="CHK-PERGUNTA", status="alerta" if known else "ok",
                       facts={"perguntas": questions, "aplica_solucao_conhecida": known},
                       fragment_ids=[q["fragmento"] for q in questions])
