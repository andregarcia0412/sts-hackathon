"""Conclusion stage: scores → per-criterion states (LLM judge + gates in code) → suggested class.

Shared by the orchestrator and the re-judge benchmark, so the path measured there is the production path.
"""

import asyncio

from pydantic import BaseModel

from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.config import Settings
from backend.criteria.schemas import CriterionResult
from backend.graph.classify import ClassSuggestion, classify
from backend.graph.scoring import RuleScore, score_criterion, score_rule
from backend.graph.states import CriterionState, judge_state, numeric_record_in
from backend.llm import LLM


class JudgeOptions(BaseModel):
    """How the judge runs; recorded in the analysis versions and in the benchmark config."""

    @classmethod
    def from_settings(cls, settings: Settings) -> "JudgeOptions":
        return cls()


class JudgeOutcome(BaseModel):
    scores: dict[str, list[RuleScore]]
    criterion_scores: dict[str, int | None]
    states: dict[str, CriterionState]
    suggestion: ClassSuggestion


def score_results(results: dict[str, CriterionResult], catalog: Catalog) -> tuple[dict[str, list[RuleScore]], dict[str, int | None]]:
    scores = {c: [score_rule(run, catalog.get(run.rule_id)) for run in result.rules] for c, result in results.items()}
    return scores, {c: score_criterion(s) for c, s in scores.items()}


async def judge_and_classify(llm: LLM, catalog: Catalog, results: dict[str, CriterionResult],
                             options: JudgeOptions | None = None) -> JudgeOutcome:
    scores, criterion_scores = score_results(results, catalog)
    numeric = numeric_record_in(results)
    judged = await asyncio.gather(*(judge_state(llm, catalog, results[c], numeric) for c in CRITERIA_ORDER))
    states = dict(zip(CRITERIA_ORDER, judged, strict=True))
    return JudgeOutcome(scores=scores, criterion_scores=criterion_scores, states=states, suggestion=classify(states))
