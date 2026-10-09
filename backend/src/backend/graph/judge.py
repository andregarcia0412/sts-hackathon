"""Conclusion stage: scores → per-criterion states (LLM judge + gates in code) → suggested class.

Shared by the orchestrator and the re-judge benchmark, so the path measured there is the production path.
"""

import asyncio

from pydantic import BaseModel

from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.criteria.schemas import CriterionResult
from backend.graph.classify import ClassSuggestion, classify
from backend.graph.options import JudgeOptions
from backend.graph.questionnaire import judge_by_questionnaire
from backend.graph.scoring import RuleScore, score_criterion, score_rule
from backend.graph.states import CriterionState, judge_state, numeric_record_in
from backend.llm import LLM

__all__ = ["JudgeOptions", "JudgeOutcome", "judge_and_classify", "rules_with_evidence", "score_results"]


class JudgeOutcome(BaseModel):
    scores: dict[str, list[RuleScore]]
    criterion_scores: dict[str, int | None]
    states: dict[str, CriterionState]
    suggestion: ClassSuggestion


def score_results(results: dict[str, CriterionResult], catalog: Catalog) -> tuple[dict[str, list[RuleScore]], dict[str, int | None]]:
    scores = {c: [score_rule(run, catalog.get(run.rule_id)) for run in result.rules] for c, result in results.items()}
    return scores, {c: score_criterion(s) for c, s in scores.items()}


def rules_with_evidence(scores: list[RuleScore]) -> int:
    """Rules that entered the criterion score (in the mean, with evidence)."""
    return sum(1 for s in scores if s.in_mean and s.score is not None)


async def judge_and_classify(llm: LLM, catalog: Catalog, results: dict[str, CriterionResult],
                             options: JudgeOptions | None = None) -> JudgeOutcome:
    options = options or JudgeOptions()
    scores, criterion_scores = score_results(results, catalog)
    numeric = numeric_record_in(results)
    if options.judge_mode == "questionario" and catalog.questionnaire is None:
        raise ValueError("JUDGE_MODE=questionario needs catalog/questionario.yaml")
    judge = judge_by_questionnaire if options.judge_mode == "questionario" else judge_state
    judged = await asyncio.gather(*(
        judge(llm, catalog, results[c], numeric, score=criterion_scores.get(c),
              n_rules=rules_with_evidence(scores.get(c, [])), options=options)
        for c in CRITERIA_ORDER
    ))
    states = dict(zip(CRITERIA_ORDER, judged, strict=True))
    return JudgeOutcome(scores=scores, criterion_scores=criterion_scores, states=states, suggestion=classify(states))
