"""Roda as 8 checagens compartilhadas uma vez por projeto (spec 5.3 + V9.1)."""
from __future__ import annotations

from ai_microservice.checks.config_check import run_chk_config
from ai_microservice.checks.diverg import run_chk_diverg
from ai_microservice.checks.escopo import run_chk_escopo
from ai_microservice.checks.falhas import run_chk_falhas
from ai_microservice.checks.pergunta import run_chk_pergunta
from ai_microservice.checks.recalcula import run_chk_recalc
from ai_microservice.checks.tempo import run_chk_tempo
from ai_microservice.checks.versoes import run_chk_versoes
from ai_microservice.extraction.parsers import Fragment

# ordem fixa; CHK-PERGUNTA é determinística e roda junto das demais
RUN_CHECKS = [
    "CHK-TEMPO", "CHK-RECALC", "CHK-VERSOES", "CHK-FALHAS",
    "CHK-CONFIG", "CHK-ESCOPO", "CHK-DIVERG", "CHK-PERGUNTA",
]


def run_all_checks(fragments: list[Fragment]) -> dict:
    return {
        "CHK-TEMPO": run_chk_tempo(fragments),
        "CHK-RECALC": run_chk_recalc(fragments),
        "CHK-VERSOES": run_chk_versoes(fragments),
        "CHK-FALHAS": run_chk_falhas(fragments),
        "CHK-CONFIG": run_chk_config(fragments),
        "CHK-ESCOPO": run_chk_escopo(fragments),
        "CHK-DIVERG": run_chk_diverg(fragments),
        "CHK-PERGUNTA": run_chk_pergunta(fragments),
    }