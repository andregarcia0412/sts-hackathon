import csv
import io

from backend.report.builder import ANSWER_KEY_COLUMNS, Parecer


def answer_key_row(parecer: Parecer) -> dict[str, str]:
    """One line in the schema of historicos_classificados.csv (27 columns)."""
    row = {
        "projeto_id": parecer.projeto_id,
        "titulo": parecer.titulo,
        "classificacao": parecer.classificacao or "",
        "justificativa": parecer.justificativa,
        "limite": parecer.limite,
        "fontes_decisivas": " | ".join(parecer.fontes_decisivas),
        "divergencia_depoimento": " ".join(parecer.divergencias),
    }
    for n, section in enumerate(parecer.criterios, start=1):
        row |= {
            f"criterio_{n}": section.criterio,
            f"estado_{n}": section.estado or "",
            f"justificativa_{n}": section.justificativa,
            f"fonte_{n}": section.fonte,
        }
    return {column: row.get(column, "") for column in ANSWER_KEY_COLUMNS}


def to_csv(rows: list[dict[str, str]]) -> str:
    """UTF-8 with BOM and semicolons, like the challenge package."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ANSWER_KEY_COLUMNS, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(rows)
    return "﻿" + buffer.getvalue()
