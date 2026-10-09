"""Server-side version of the front-end ProjectQuery (filters, sort and pagination of the project list)."""

from datetime import date, datetime, time, timedelta
from typing import Literal, get_args

from pydantic import BaseModel, Field

from backend.projects.models import ProjectStatus
from backend.projects.schemas import ProjectPage, ProjectSummary

ProjectSort = Literal["recent", "oldest", "name", "weakest"]
ScoreBand = Literal["strong", "moderate", "weak"]
STRONG_MIN = 70
MODERATE_MIN = 40


class ProjectQuery(BaseModel):
    search: str | None = None
    statuses: list[ProjectStatus] = Field(default_factory=list)
    weakest_band: ScoreBand | None = None
    outcome: str | None = None  # a DecisionOutcome or "none"
    date_from: date | None = None
    date_to: date | None = None
    sort: ProjectSort = "recent"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


def score_band(score: float) -> ScoreBand:
    if score >= STRONG_MIN:
        return "strong"
    return "moderate" if score >= MODERATE_MIN else "weak"


def weakest_score(item: ProjectSummary) -> float | None:
    scores = [c.score for c in item.score_summary or [] if c.score is not None]
    return min(scores) if scores else None


def _matches(item: ProjectSummary, query: ProjectQuery) -> bool:
    if query.search:
        needle = query.search.casefold()
        haystack = " ".join(filter(None, [item.name, item.company, item.code, item.free_text])).casefold()
        if needle not in haystack:
            return False
    if query.statuses and item.status not in query.statuses:
        return False
    if query.weakest_band:
        weakest = weakest_score(item)
        if weakest is None or score_band(weakest) != query.weakest_band:
            return False
    if query.outcome:
        current = item.last_decision.outcome if item.last_decision else "none"
        if current != query.outcome:
            return False
    created = item.created_at.replace(tzinfo=None) if item.created_at.tzinfo else item.created_at
    if query.date_from and created < datetime.combine(query.date_from, time.min):
        return False
    if query.date_to and created >= datetime.combine(query.date_to + timedelta(days=1), time.min):
        return False
    return True


def _sort_key(query: ProjectQuery):
    if query.sort == "name":
        return lambda item: item.name.casefold()
    if query.sort == "weakest":
        return lambda item: (weakest_score(item) is None, weakest_score(item) or 0)
    return lambda item: item.created_at


def apply_project_query(items: list[ProjectSummary], query: ProjectQuery) -> ProjectPage:
    counts = {status: 0 for status in get_args(ProjectStatus)}
    for item in items:
        counts[item.status] += 1
    matched = sorted(
        (item for item in items if _matches(item, query)),
        key=_sort_key(query),
        reverse=query.sort == "recent",
    )
    start = (query.page - 1) * query.page_size
    return ProjectPage(
        items=matched[start : start + query.page_size],
        total=len(matched),
        page=query.page,
        page_size=query.page_size,
        status_counts=counts,
    )
