from backend.benchmark.reference import load_answer_key, load_preliminary
from backend.catalog.loader import get_catalog
from backend.report.builder import ANSWER_KEY_COLUMNS


def write(path, header, rows):
    path.write_text("﻿" + "\n".join([";".join(header), *(";".join(r) for r in rows)]), encoding="utf-8")
    return path


def test_answer_key_maps_criteria_by_name(tmp_path):
    names = ["Novidade", "Criatividade técnica", "Incerteza tecnológica", "Sistematicidade", "Transferência/reprodução"]
    states = ["NÃO DEMONSTRADA", "NÃO DEMONSTRADA", "NÃO CARACTERIZADA", "DOCUMENTADA COMO ACEITE",
              "DOCUMENTADA PARA A CONFIGURAÇÃO"]
    row = {"projeto_id": "PRJ01", "classificacao": "Não elegível"}
    for n, (name, state) in enumerate(zip(names, states, strict=True), start=1):
        row |= {f"criterio_{n}": name, f"estado_{n}": state}
    path = write(tmp_path / "key.csv", ANSWER_KEY_COLUMNS, [[row.get(c, "") for c in ANSWER_KEY_COLUMNS]])
    [case] = load_answer_key(path, get_catalog()).values()
    assert case.source == "oficial" and case.expected_class == "not_eligible"
    assert case.states == {"NOV": "NÃO DEMONSTRADA", "CRI": "NÃO DEMONSTRADA", "INC": "NÃO CARACTERIZADA",
                           "SIS": "DOCUMENTADA COMO ACEITE", "REP": "DOCUMENTADA PARA A CONFIGURAÇÃO"}


def test_preliminary_reading_with_and_without_planted_divergence(tmp_path):
    header = ["projeto_id", "classificacao", "divergencia_entrevista", "divergencia_registro", "fonte_que_prevalece"]
    path = write(tmp_path / "pre.csv", header, [["PRJ40", "Com ressalvas", "400", "412", "PRJ40-S01"],
                                                ["PRJ28", "Evidência insuficiente", "", "", ""]])
    cases = load_preliminary(path)
    assert cases["PRJ40"].source == "preliminar" and cases["PRJ40"].expected_class == "eligible_with_caveats"
    assert cases["PRJ40"].planted_divergences[0].record == "412"
    assert cases["PRJ28"].planted_divergences == [] and cases["PRJ28"].states == {}
