from datetime import UTC, datetime, timedelta

import pytest

from backend.benchmark.metrics import accuracy, compute, determinism, distribution, divergence_found, evidence, timing
from backend.benchmark.models import DivergenceSnapshot, RunSnapshot
from backend.benchmark.reference import ExpectedCase, PlantedDivergence
from backend.catalog.loader import get_catalog
from backend.llm.usage import LLMUsage, RoleUsage

T0 = datetime(2026, 10, 1, tzinfo=UTC)
NOV_POS, NOV_NEG = "DEMONSTRADA NO RECORTE", "NÃO DEMONSTRADA"


def snap(code, cls, repeat=1, states=None, total_s=10.0, status="concluida", **extra) -> RunSnapshot:
    states = states or {"NOV": NOV_POS}
    columns = {c: ("pd" if s == NOV_POS else "rotina") for c, s in states.items()}
    return RunSnapshot(set="historico", code=code, repeat=repeat, analysis_id=f"a-{code}-{repeat}", status=status,
                       suggested_class=cls, states=states, columns=columns, total_s=total_s,
                       started_at=T0, finished_at=T0 + timedelta(seconds=total_s), **extra)


def case(code, cls, source="oficial", states=None, planted=None) -> ExpectedCase:
    return ExpectedCase(code=code, source=source, expected_class=cls, states=states or {"NOV": NOV_POS},
                        planted_divergences=planted or [])


def test_distribution_uses_nearest_rank_p95():
    d = distribution(range(1, 21))
    assert (d.median, d.p95, d.max, d.n) == (10.5, 19, 20, 20)
    assert distribution([]).n == 0


def test_accuracy_confusion_f1_kappa_and_costly_errors():
    runs = [snap("P1", "eligible"), snap("P2", "eligible"), snap("P3", "not_eligible"), snap("P4", None)]
    expected = {"P1": case("P1", "eligible"), "P2": case("P2", "not_eligible"), "P3": case("P3", "not_eligible"),
                "P4": case("P4", "insufficient_evidence")}
    m = accuracy(runs, expected, "oficial", get_catalog())
    assert (m.n, m.class_hits, m.class_accuracy) == (4, 2, 0.5)
    assert m.confusion["Não elegível"] == {"Elegível": 1, "Não elegível": 1}
    assert m.confusion["Evidência insuficiente"] == {"(sem classe)": 1}
    assert m.false_eligible == 1 and m.false_not_eligible == 0
    assert m.per_class["Elegível"].precision == 0.5 and m.per_class["Elegível"].recall == 1.0
    assert m.per_class["Evidência insuficiente"].f1 == 0.0
    assert m.cohen_kappa is not None and m.cohen_kappa < 0.5
    assert "P2: Não elegível → Elegível" in m.misses


def test_state_and_column_accuracy_only_where_the_key_has_a_state():
    runs = [snap("P1", "eligible", states={"NOV": NOV_POS}), snap("P2", "eligible", states={"NOV": NOV_POS})]
    expected = {"P1": case("P1", "eligible", states={"NOV": NOV_POS}),
                "P2": case("P2", "not_eligible", states={"NOV": NOV_NEG})}
    m = accuracy(runs, expected, "oficial", get_catalog())
    assert m.state_accuracy == {"NOV": 0.5}
    assert m.column_accuracy == {"NOV": 0.5}


def test_references_are_never_mixed():
    runs = [snap("P1", "eligible"), snap("P21", "eligible")]
    expected = {"P1": case("P1", "eligible"), "P21": case("P21", "not_eligible", source="preliminar")}
    metrics = compute(runs, expected, get_catalog())
    assert metrics.accuracy["oficial"].class_accuracy == 1.0
    assert metrics.accuracy["preliminar"].class_accuracy == 0.0


@pytest.mark.parametrize(("planted", "testimony", "record", "found"), [
    (PlantedDivergence(testimony="400", record="412"), "sinalizou 400 decisões", "412 sinalizadas", True),
    (PlantedDivergence(testimony="400", record="412"), "sinalizou 4000 decisões", "412 sinalizadas", False),
    (PlantedDivergence(testimony="1,20", record="1,42"), "p95 foi 1,20 segundo", "p95 = 1.42 s", True),
    (PlantedDivergence(testimony="zerou", record="60"), "A confirmação Zerou as leituras", "60 de 30.000", True),
    (PlantedDivergence(testimony="41/50", record="38/46"), "41/50 respostas", "38/46 trechos", True),
])
def test_planted_divergence_matching(planted, testimony, record, found):
    divergence = DivergenceSnapshot(criterion="INC", testimony_quote=testimony, record_quote=record, statement="")
    assert divergence_found(planted, [divergence]) is found


def test_planted_divergence_recall():
    hit = DivergenceSnapshot(criterion="INC", testimony_quote="400", record_quote="412", statement="")
    runs = [snap("P40", "eligible", divergences=[hit]), snap("P38", "eligible")]
    expected = {"P40": case("P40", "eligible", "preliminar", planted=[PlantedDivergence(testimony="400", record="412")]),
                "P38": case("P38", "eligible", "preliminar", planted=[PlantedDivergence(testimony="1,20", record="1,42")])}
    m = accuracy(runs, expected, "preliminar", get_catalog())
    assert (m.planted_divergences, m.planted_divergences_found, m.planted_divergence_recall) == (2, 1, 0.5)


def test_timing_wall_clock_and_throughput():
    runs = [snap("P1", "eligible", total_s=100, stage_seconds={"NOV": 40}),
            snap("P2", "eligible", total_s=200, stage_seconds={"NOV": 60})]
    t = timing(runs)
    assert t.total_s.mean == 150 and t.stages_s["NOV"].median == 50
    assert t.wall_clock_s == 200 and t.projects_per_hour == 36


def test_evidence_gate_drop_rate_and_coverage():
    runs = [snap("P1", "eligible", evidences_positive=3, evidences_negative=1, gate_dropped=1,
                 rules_total=10, rules_with_evidence=4, web_searches=4, web_search_errors=1)]
    e = evidence(runs)
    assert (e.positive_share, e.gate_drop_rate, e.rule_coverage, e.web_search_error_rate) == (0.75, 0.2, 0.4, 0.25)


def test_determinism_only_with_repeats():
    assert determinism([snap("P1", "eligible")]) is None
    runs = [snap("P1", "eligible", evidence_ids=["a", "b"], criterion_scores={"NOV": 80}),
            snap("P1", "eligible", repeat=2, evidence_ids=["a"], criterion_scores={"NOV": 60}),
            snap("P2", "eligible"), snap("P2", "not_eligible", repeat=2)]
    d = determinism(runs)
    assert d.projects == 2 and d.class_agreement == 0.5
    assert d.score_std["NOV"] == 10 and d.evidence_jaccard == 0.75
    assert d.unstable == ["P2: Elegível / Não elegível"]


def test_usage_and_reliability_in_compute():
    usage = LLMUsage(roles={"doc": RoleUsage(calls=3, prompt_tokens=100, completion_tokens=10)}, web_search_calls=2)
    runs = [snap("P1", "eligible", usage=usage, stages={"NOV": "concluida"}),
            snap("P2", None, status="falhou", stages={"NOV": "nao_executada"})]
    m = compute(runs, {}, get_catalog())
    assert m.usage.total.calls == 3 and m.usage.tokens_per_run.mean == 110 and m.usage.web_search_calls == 2
    assert m.reliability.failure_rate == 0.5 and m.reliability.stage_failures == {"NOV": 1}
    assert m.reliability.no_class_rate == 0.5
    assert m.accuracy == {} and m.class_distribution["sugerida"] == {"Elegível": 1, "(sem classe)": 1}
