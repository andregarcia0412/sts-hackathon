import pytest

from backend.catalog.loader import get_catalog
from backend.frontend_api.projection import distribute, project_analysis
from tests.factories import analysed_project


def test_distribute_keeps_the_total():
    assert distribute(67, [1, 1, 1]) == [23, 22, 22]
    assert sum(distribute(50, [33.3, 33.3, 33.4])) == 50
    assert distribute(0, []) == []


@pytest.fixture
async def projected(db):
    project, analysis = await analysed_project()
    return project, analysis, project_analysis(get_catalog(), analysis, project, contestations=[])


async def test_tree_ids_and_criteria_order(projected):
    _, analysis, view = projected
    assert view.framework == "frascati"
    assert view.project_id
    assert [c.id for c in view.criteria] == ["crit-novelty", "crit-creativity", "crit-uncertainty",
                                             "crit-systematicity", "crit-reproducibility"]
    novelty = view.criteria[0]
    assert novelty.key == "novelty" and novelty.name == "Novidade"
    assert novelty.state == "DEMONSTRADA NO RECORTE"
    rule = next(r for r in novelty.rules if r.code == "NOV-D2")
    assert rule.id == "rule-nov-d2"
    assert rule.counts.positive == 1 and rule.score == 100
    assert rule.normative_source.label.startswith("Guia MCTI")


async def test_evidence_has_verbatim_excerpt_and_document(projected):
    project, _, view = projected
    rule = next(r for r in view.criteria[0].rules if r.code == "NOV-D2")
    [evidence] = rule.evidences
    assert evidence.polarity == "positive"
    assert evidence.project_excerpt.excerpt == "Ambos falham quando dois lotes dependem do mesmo saldo."
    assert evidence.project_excerpt.file_name == "evidencias/metodo.md"
    method_doc = next(d for d in project.active_documents() if d.file_name == "evidencias/metodo.md")
    assert evidence.project_excerpt.document_id == method_doc.id
    assert evidence.source.alias == "evidencias/metodo.md#1"


async def test_web_evidence_has_reference_url(projected):
    _, _, view = projected
    rule = next(r for r in view.criteria[0].rules if r.code == "NOV-W3")
    assert rule.evidences[0].references[0].url == "https://doi.org/p"
    assert rule.evidences[0].project_excerpt is None


async def test_score_explanations_add_up(projected):
    _, _, view = projected
    for criterion in view.criteria:
        if criterion.score is not None:
            assert sum(f.points for f in criterion.score_explanation.factors) + criterion.score_explanation.baseline == criterion.score
        for rule in criterion.rules:
            if rule.score is not None:
                assert sum(f.points for f in rule.score_explanation.factors) == rule.score


async def test_rules_without_evidence_have_no_score_and_a_reason(projected):
    _, _, view = projected
    na = next(r for c in view.criteria for r in c.rules if r.code == "SIS-D4")
    assert na.score is None and na.status == "na" and na.status_reason


async def test_class_divergences_and_versions(projected):
    _, analysis, view = projected
    assert view.suggested_class == "eligible"
    assert view.inconsistent is False
    assert view.divergences[0].statement.startswith("A entrevista afirma")
    assert view.versions.catalog_version == get_catalog().versao
    assert view.generated_at == analysis.finished_at
