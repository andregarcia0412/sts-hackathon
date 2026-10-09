import pytest

from backend.graph.classify import classify
from backend.graph.states import Caveat, CriterionState, MissingLinkInfo

PD = {"NOV": "DEMONSTRADA NO RECORTE", "CRI": "DEMONSTRADA NO RECORTE", "INC": "INVESTIGADA", "SIS": "DOCUMENTADA"}
ROT = {"NOV": "NÃO DEMONSTRADA", "CRI": "NÃO DEMONSTRADA", "INC": "NÃO CARACTERIZADA", "SIS": "DOCUMENTADA COMO ACEITE",
       "REP": "DOCUMENTADA PARA A CONFIGURAÇÃO"}
INS = {"NOV": "INDETERMINADA", "CRI": "INDETERMINADA", "INC": "ALEGADA, NÃO VERIFICÁVEL", "SIS": "PARCIAL",
       "REP": "INSUFICIENTE PARA O NÚCLEO ALEGADO"}


def states(values: dict[str, str], **extra) -> dict[str, CriterionState]:
    return {c: CriterionState.of(c, v, **extra.get(c, {})) for c, v in values.items()}


def test_exact_patterns():
    assert classify(states(PD | {"REP": "DOCUMENTADA NO ESCOPO"})).suggested_class == "eligible"
    assert classify(states(ROT)).suggested_class == "not_eligible"
    insufficient = classify(states(INS, NOV={"missing_link": MissingLinkInfo(elo_ausente="saídas", evidencias_a_solicitar=["log"])}))
    assert insufficient.suggested_class == "insufficient_evidence"
    assert insufficient.missing_link.elo_ausente == "saídas"
    assert not insufficient.inconsistent


def test_caveats_need_scope_limit_and_evidence():
    caveat = Caveat(recorte_sustentado="r", limitacao="l", evidencia_necessaria="e")
    result = classify(states(PD | {"REP": "DOCUMENTADA COM LIMITE"}, REP={"caveat": caveat}))
    assert result.suggested_class == "eligible_with_caveats"
    assert result.caveat == caveat
    assert result.incomplete == []
    missing = classify(states(PD | {"REP": "DOCUMENTADA COM LIMITE"}))
    assert missing.incomplete


@pytest.mark.parametrize("mix,expected", [
    (PD | {"INC": "ALEGADA, NÃO VERIFICÁVEL", "REP": "DOCUMENTADA NO ESCOPO"}, "insufficient_evidence"),
    (PD | {"NOV": "NÃO DEMONSTRADA", "REP": "DOCUMENTADA NO ESCOPO"}, "not_eligible"),
    (ROT | {"INC": "ALEGADA, NÃO VERIFICÁVEL"}, "insufficient_evidence"),
    (PD | {"SIS": "DOCUMENTADA COMO ACEITE", "REP": "DOCUMENTADA NO ESCOPO"}, "insufficient_evidence"),
    (PD | {"SIS": "PARCIAL", "REP": "DOCUMENTADA COM LIMITE"}, "insufficient_evidence"),
    (ROT | {"SIS": "DOCUMENTADA", "REP": "DOCUMENTADA NO ESCOPO"}, "not_eligible"),
])
def test_mixed_vectors_use_the_tree_and_are_flagged(mix, expected):
    result = classify(states(mix))
    assert result.suggested_class == expected
    assert result.inconsistent
    assert result.path


def test_missing_state_gives_no_class():
    vector = states(PD | {"REP": "DOCUMENTADA NO ESCOPO"})
    vector["INC"] = CriterionState(criterion="INC", state=None, error="falhou")
    result = classify(vector)
    assert result.suggested_class is None
    assert result.inconsistent
