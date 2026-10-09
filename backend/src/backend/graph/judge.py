"""Conclusion stage: scores → per-criterion states (LLM judge + gates in code) → suggested class.

Shared by the orchestrator and the re-judge benchmark, so the path measured there is the production path.
"""

import asyncio

from pydantic import BaseModel

from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.checks.models import ChecksReport
from backend.criteria.schemas import CriterionResult
from backend.graph.classify import ClassSuggestion, classify
from backend.graph.consistency import ConsistencyReport, apply_consistency
from backend.graph.options import JudgeOptions
from backend.graph.questionnaire import judge_by_questionnaire
from backend.graph.scoring import RuleScore, score_criterion, score_rule
from backend.graph.states import CriterionState, judge_state, numeric_record_in
from backend.llm import LLM

FIRST_WAVE = ("NOV", "CRI")
SECOND_WAVE = ("INC", "SIS", "REP")

__all__ = ["JudgeOptions", "JudgeOutcome", "judge_and_classify", "rules_with_evidence", "score_results"]


class JudgeOutcome(BaseModel):
    scores: dict[str, list[RuleScore]]
    criterion_scores: dict[str, int | None]
    states: dict[str, CriterionState]
    suggestion: ClassSuggestion
    consistency: ConsistencyReport | None = None


def score_results(results: dict[str, CriterionResult], catalog: Catalog) -> tuple[dict[str, list[RuleScore]], dict[str, int | None]]:
    scores = {c: [score_rule(run, catalog.get(run.rule_id)) for run in result.rules] for c, result in results.items()}
    return scores, {c: score_criterion(s) for c, s in scores.items()}


def rules_with_evidence(scores: list[RuleScore]) -> int:
    """Rules that entered the criterion score (in the mean, with evidence)."""
    return sum(1 for s in scores if s.in_mean and s.score is not None)


async def judge_and_classify(llm: LLM, catalog: Catalog, results: dict[str, CriterionResult],
                             options: JudgeOptions | None = None, checks: ChecksReport | None = None) -> JudgeOutcome:
    options = options or JudgeOptions()
    consistency = None
    if options.consistency_neutralize or options.consistency_inc_d2:  # before the score: it changes what counts
        consistency = apply_consistency(results, catalog, options.consistency_text_markers, checks=checks,
                                        neutralize=options.consistency_neutralize,
                                        inc_d2=options.consistency_inc_d2)
    scores, criterion_scores = score_results(results, catalog)
    numeric = numeric_record_in(results)
    if options.judge_mode == "questionario" and catalog.questionnaire is None:
        raise ValueError("JUDGE_MODE=questionario needs catalog/questionario.yaml")
    judge = judge_by_questionnaire if options.judge_mode == "questionario" else judge_state

    async def one(criterion: str, cross: set[str]) -> CriterionState:
        return await judge(llm, catalog, results[criterion], numeric, score=criterion_scores.get(criterion),
                           n_rules=rules_with_evidence(scores.get(criterion, [])), options=options, cross=cross,
                           checks=checks)

    # Two waves, no extra calls: the state gates that fired in NOV/CRI feed the cross-criteria gates of INC/SIS/REP.
    first = await asyncio.gather(*(one(c, set()) for c in FIRST_WAVE))
    cross = {rule_id for state in first for rule_id in state.fired_gates}
    second = await asyncio.gather(*(one(c, cross) for c in SECOND_WAVE))
    judged = {**dict(zip(FIRST_WAVE, first, strict=True)), **dict(zip(SECOND_WAVE, second, strict=True))}
    states = {c: judged[c] for c in CRITERIA_ORDER}
    return JudgeOutcome(scores=scores, criterion_scores=criterion_scores, states=states, suggestion=classify(states),
                        consistency=consistency)
