from backend.catalog.loader import get_catalog
from backend.criteria.schemas import CriterionResult
from backend.graph.scoring import score_criterion, score_rule
from tests.factories import evidence, run


def test_rule_score_is_positives_over_total():
    rule = get_catalog().get("NOV-D2")
    score = score_rule(run("NOV-D2", evidence("NOV-D2", source="a"), evidence("NOV-D2", source="b"),
                           evidence("NOV-D2", "negativa", source="c")), rule)
    assert (score.positive, score.negative, score.score) == (2, 1, 67)


def test_tie_is_fifty_no_odd_rule():
    rule = get_catalog().get("NOV-D2")
    score = score_rule(run("NOV-D2", evidence("NOV-D2", source="a"), evidence("NOV-D2", "negativa", source="b")), rule)
    assert score.score == 50


def test_same_source_counts_once_per_rule():
    rule = get_catalog().get("NOV-D2")
    score = score_rule(run("NOV-D2", evidence("NOV-D2", source="a", quote="x"), evidence("NOV-D2", source="a", quote="y")), rule)
    assert (score.positive, score.score) == (1, 100)


def test_no_evidence_is_none_not_zero():
    rule = get_catalog().get("NOV-D2")
    assert score_rule(run("NOV-D2"), rule).score is None


def test_criterion_mean_excludes_informative_and_empty_rules():
    catalog = get_catalog()
    result = CriterionResult(criterion="NOV", rules=[
        run("NOV-D2", evidence("NOV-D2")),  # 100
        run("NOV-D1", evidence("NOV-D1", "negativa")),  # 0
        run("NOV-W1", evidence("NOV-W1")),  # informative, out of the mean
        run("NOV-D3"),  # no evidence
        run("NOV-D8", status="na", reason="x"),
    ])
    scores = [score_rule(r, catalog.get(r.rule_id)) for r in result.rules]
    assert score_criterion(scores) == 50
    assert next(s for s in scores if s.rule_id == "NOV-W1").in_mean is False


def test_criterion_without_any_scored_rule_is_none():
    assert score_criterion([score_rule(run("NOV-D3"), get_catalog().get("NOV-D3"))]) is None
