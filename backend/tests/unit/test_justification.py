import pytest

from backend.criteria.justification import FLAG, flags_for, speculative


@pytest.mark.parametrize("text, expected", [
    ("pode gerar comportamento inesperado, caracterizando risco", True),
    ("o trecho mostra que pode gerar comportamento inesperado", False),
    ("O resultado apresenta contagem 183/300, que pode ser recalculada a partir das medições primárias.", False),
    ("Possivelmente reduz a latência.", True),
    ("O texto explicita a janela.", False),
])
def test_speculative_without_anchor(text, expected):
    assert speculative(text) is expected


def test_the_flag_never_removes_the_evidence_nor_changes_the_score():
    from backend.catalog.loader import get_catalog
    from backend.graph.scoring import score_rule
    from tests.factories import evidence, run

    item = evidence("INC-D1", quote="q")
    item.explanation = "pode gerar comportamento inesperado"
    item.flags = flags_for(item.explanation, enabled=True)
    assert item.flags == [FLAG] and flags_for(item.explanation, enabled=False) == []
    rule = run("INC-D1", item)
    assert score_rule(rule, get_catalog().get("INC-D1")).score == 100 and rule.evidences == [item]


async def test_doc_sub_marks_only_when_enabled():
    from backend.catalog.loader import get_catalog
    from backend.criteria.doc_sub import DocSubOut, run_doc_sub
    from tests.factories import synthetic_canonical
    from tests.fakes import FakeLLM

    out = DocSubOut(evidencias=[{"regra_id": "SIS-D12", "fragmento_id": "PRJ90-S02", "quote": "196;200",
                                 "polaridade": "positiva", "justificativa": "talvez seja um ensaio"}],
                    regras_sem_evidencia=[], divergencias=[], elos_ausentes=[])
    canonical = await synthetic_canonical()
    rules = get_catalog().rules_for("SIS", "doc")
    for enabled in (False, True):
        result = await run_doc_sub(FakeLLM({DocSubOut: out}), get_catalog(), "SIS", rules, canonical, 300,
                                   flag_speculative=enabled)
        [item] = result.rule("SIS-D12").evidences
        assert (item.flags == [FLAG]) is enabled
