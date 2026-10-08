from datetime import UTC, datetime

from backend.frontend_api.project_query import ProjectQuery, apply_project_query
from backend.projects.schemas import CriterionScoreSummary, LastDecision, ProjectSummary


def item(name, day, status="ready", scores=(80, 50), outcome=None):
    return ProjectSummary(
        id=name,
        owner_id="u",
        name=name,
        created_at=datetime(2026, 10, day, tzinfo=UTC),
        status=status,
        documents=[],
        score_summary=[CriterionScoreSummary(criterion_key=f"c{i}", name="c", score=s) for i, s in enumerate(scores)],
        last_decision=LastDecision(outcome=outcome, decided_at=datetime(2026, 10, 9, tzinfo=UTC), analyst_name="A")
        if outcome
        else None,
    )


ITEMS = [
    item("Alfa", 1, scores=(90, 85)),
    item("Beta", 2, status="processing", scores=()),
    item("Gama", 3, scores=(30, 90), outcome="not_eligible"),
]


def test_default_sort_is_recent_first_and_counts_statuses():
    page = apply_project_query(ITEMS, ProjectQuery())
    assert [i.name for i in page.items] == ["Gama", "Beta", "Alfa"]
    assert page.status_counts == {"processing": 1, "ready": 2, "decided": 0, "error": 0}


def test_filters():
    assert [i.name for i in apply_project_query(ITEMS, ProjectQuery(search="alf")).items] == ["Alfa"]
    assert [i.name for i in apply_project_query(ITEMS, ProjectQuery(statuses=["processing"])).items] == ["Beta"]
    assert [i.name for i in apply_project_query(ITEMS, ProjectQuery(weakest_band="weak")).items] == ["Gama"]
    assert [i.name for i in apply_project_query(ITEMS, ProjectQuery(outcome="none", sort="name")).items] == ["Alfa", "Beta"]
    ranged = apply_project_query(ITEMS, ProjectQuery(date_from="2026-10-02", date_to="2026-10-02"))
    assert [i.name for i in ranged.items] == ["Beta"]


def test_weakest_sort_puts_projects_without_scores_last():
    assert [i.name for i in apply_project_query(ITEMS, ProjectQuery(sort="weakest")).items] == ["Gama", "Alfa", "Beta"]


def test_pagination():
    page = apply_project_query(ITEMS, ProjectQuery(page=2, page_size=2))
    assert page.total == 3 and [i.name for i in page.items] == ["Alfa"]
