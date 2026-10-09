"""Module 2: one generic agent per criterion (sub Web + sub Doc), orchestrated in code, not by an LLM."""

import asyncio
import inspect
from collections.abc import Callable

from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.criteria.doc_sub import run_doc_sub
from backend.criteria.schemas import ClosestDoc, CriterionResult, RuleRun
from backend.criteria.web_sub import run_web_sub
from backend.errors import safe_error_message
from backend.extraction.schema import CanonicalProject
from backend.llm import LLM
from backend.search.base import SearchProvider

StageCallback = Callable[..., object]
FIRST_WAVE = ("NOV", "SIS", "REP")
SECOND_WAVE = ("CRI", "INC")  # read the closest document found by Novelty (same state of the art for all)


def _merge(criterion: str, parts: list[CriterionResult], catalog: Catalog) -> CriterionResult:
    merged = CriterionResult(criterion=criterion)
    for part in parts:
        merged.rules += part.rules
        merged.divergences += part.divergences
        merged.missing_links += part.missing_links
        merged.web_sources += part.web_sources
        merged.search_log += part.search_log
        merged.errors += part.errors
        merged.closest_doc = merged.closest_doc or part.closest_doc
    order = {rule.id: index for index, rule in enumerate(catalog.rules)}
    merged.rules.sort(key=lambda run: order.get(run.rule_id, 0))
    return merged


class CriteriaRunner:
    def __init__(
        self,
        llm: LLM,
        catalog: Catalog,
        providers: dict[str, SearchProvider],
        on_stage: StageCallback | None = None,
        queries_per_front: int = 3,
        results_per_query: int = 5,
        fetch_per_front: int = 6,
        max_table_rows: int = 300,
        doc_pitfalls: bool = False,
    ) -> None:
        self.llm, self.catalog, self.providers = llm, catalog, providers
        self._on_stage = on_stage
        self.queries_per_front, self.results_per_query = queries_per_front, results_per_query
        self.fetch_per_front, self.max_table_rows = fetch_per_front, max_table_rows
        self.doc_pitfalls = doc_pitfalls

    async def on_stage(self, name: str, status: str, error: str | None = None) -> None:
        if self._on_stage is None:
            return
        outcome = self._on_stage(name, status, error)
        if inspect.isawaitable(outcome):
            await outcome

    async def run_criterion(self, criterion: str, canonical: CanonicalProject, closest: ClosestDoc | None = None) -> CriterionResult:
        await self.on_stage(criterion, "rodando")
        web_rules = self.catalog.rules_for(criterion, "web")
        doc_rules = self.catalog.rules_for(criterion, "doc")
        tasks = [run_doc_sub(self.llm, self.catalog, criterion, doc_rules, canonical, self.max_table_rows,
                             pitfalls=self.doc_pitfalls)]
        if web_rules:
            tasks.append(
                run_web_sub(self.llm, self.catalog, criterion, web_rules, canonical, self.providers,
                            self.queries_per_front, self.results_per_query, self.fetch_per_front, closest)
            )
        try:
            parts = await asyncio.gather(*tasks)
        except Exception as error:  # defensive: a sub-agent bug must not take the whole analysis down
            message = safe_error_message(error)
            await self.on_stage(criterion, "falhou", message)
            rules = web_rules + doc_rules
            return CriterionResult(
                criterion=criterion,
                errors=[message],
                rules=[RuleRun(rule_id=r.id, criterion=criterion, status="nao_executada", reason=f"falha: {message}")
                       for r in rules],
            )
        result = _merge(criterion, list(parts), self.catalog)
        await self.on_stage(criterion, "falhou" if result.errors else "concluida", "; ".join(result.errors) or None)
        return result

    async def run_all(self, canonical: CanonicalProject) -> dict[str, CriterionResult]:
        first = await asyncio.gather(*(self.run_criterion(c, canonical) for c in FIRST_WAVE))
        results = dict(zip(FIRST_WAVE, first, strict=True))
        closest = results["NOV"].closest_doc
        second = await asyncio.gather(*(self.run_criterion(c, canonical, closest) for c in SECOND_WAVE))
        results.update(zip(SECOND_WAVE, second, strict=True))
        return {c: results[c] for c in CRITERIA_ORDER}
