from backend.catalog.loader import get_catalog
from backend.criteria.schemas import CriterionResult
from backend.graph.consistency import apply_consistency
from backend.graph.judge import JudgeOptions, judge_and_classify
from backend.graph.scoring import score_rule
from backend.graph.states import StateJudgeOut, _describe
from tests.factories import evidence, fake_state, run
from tests.fakes import FakeLLM

MANUAL = "PRJ90-EV06#1"


def results(nov_rule="NOV-D5", explanation="O manual já fornecia a função."):
    nov = evidence(nov_rule, "negativa", source=MANUAL)
    nov.explanation = explanation
    cri = evidence("CRI-D10", source=MANUAL)
    cri_other = evidence("CRI-D1", source="PRJ90-EV06#2")
    inc_numeric = evidence("INC-D12", source=MANUAL, nature="registro_primario")
    inc_negative = evidence("INC-D1", "negativa", source=MANUAL)
    return {
        "NOV": CriterionResult(criterion="NOV", rules=[run(nov_rule, nov)]),
        "CRI": CriterionResult(criterion="CRI", rules=[run("CRI-D10", cri), run("CRI-D1", cri_other)]),
        "INC": CriterionResult(criterion="INC", rules=[run("INC-D12", inc_numeric), run("INC-D1", inc_negative)]),
    }, cri, cri_other, inc_numeric, inc_negative


def test_positive_evidence_on_the_prior_reference_is_neutralized_and_leaves_the_score():
    data, cri, cri_other, inc_numeric, inc_negative = results()
    report = apply_consistency(data, get_catalog())
    assert report.reference_sources == {MANUAL: "NOV-D5"}
    assert [n.evidence_id for n in report.neutralized] == [cri.id]
    assert cri.polarity == "positiva" and cri.adjustment.by_rule == "NOV-D5"  # never deleted, polarity kept
    assert cri in data["CRI"].rule("CRI-D10").evidences
    assert score_rule(data["CRI"].rule("CRI-D10"), get_catalog().get("CRI-D10")).score is None
    assert "neutralizada por NOV-D5" in _describe(data["CRI"])
    # other sources, negative evidence and the primary measurement are never neutralized
    assert cri_other.adjustment is None and inc_negative.adjustment is None and inc_numeric.adjustment is None


def test_text_marker_alone_only_warns_unless_enabled():
    data, cri, *_ = results(nov_rule="NOV-D2", explanation="A referência anterior já fornecia a função.")
    report = apply_consistency(data, get_catalog())
    assert report.neutralized == [] and report.warnings and cri.adjustment is None
    data, cri, *_ = results(nov_rule="NOV-D2", explanation="A referência anterior já estava em uso.")
    report = apply_consistency(data, get_catalog(), use_text_markers=True)
    assert [n.by_rule for n in report.neutralized] == ["NOV-D2"]


def test_containment_wording_the_ported_regex_missed():
    from backend.graph.consistency import CONTAINMENT_RE

    for text in ("a solução já estava descrita", "a função já existia no produto", "faixa já admitida"):
        assert CONTAINMENT_RE.search(text), text


async def test_neutralization_runs_only_behind_the_flag(db):
    from tests.factories import analysed_project

    _, analysis = await analysed_project()
    off = await judge_and_classify(FakeLLM({StateJudgeOut: fake_state()}), get_catalog(),
                                   analysis.model_copy(deep=True).criteria)
    assert off.consistency is None
    on = await judge_and_classify(FakeLLM({StateJudgeOut: fake_state()}), get_catalog(),
                                  analysis.model_copy(deep=True).criteria, JudgeOptions(consistency_neutralize=True))
    assert on.consistency is not None
