import pytest

from backend.analyses.models import Analysis, CanonicalRecord
from backend.analyses.orchestrator import STAGES, AnalysisService
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.criteria.doc_sub import DocSubOut
from backend.graph.models import GraphNode
from backend.projects.models import Project
from backend.projects.service import create_project
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM

SETTINGS = Settings(_env_file=None, ollama_model="fake-model")


def service(llm=None):
    return AnalysisService(llm or FakeLLM(full_handlers()), lambda: fake_providers(), SETTINGS, get_catalog())


@pytest.fixture
async def project(db):
    return await create_project("owner-1", "PRJ90 fila", synthetic_package())


async def test_full_pipeline_records_stages_versions_and_graph(project):
    svc = service()
    analysis = await svc.create(project)
    assert analysis.status == "pendente"
    assert [s.name for s in analysis.stages] == list(STAGES)

    done = await svc.run(str(analysis.id))
    assert done.status == "concluida"
    assert all(s.status == "concluida" for s in done.stages), [(s.name, s.status, s.error) for s in done.stages]
    assert all(s.duration_s is not None for s in done.stages)
    assert done.total_s is not None
    assert done.versions.catalog_version == get_catalog().versao
    assert done.versions.schema_version == "1.0"
    assert done.versions.models["doc"] == "fake-doc"
    assert "criteria.doc" in done.versions.prompts
    assert set(done.versions.file_hashes) == {d.file_name for d in project.active_documents()}

    assert done.suggestion.suggested_class == "eligible"
    assert done.states["INC"].state == "INVESTIGADA"
    assert done.criterion_scores["NOV"] == 100
    assert await CanonicalRecord.find_one(CanonicalRecord.analysis_id == str(done.id))
    assert await GraphNode.find(GraphNode.analysis_id == str(done.id)).count() > 10

    refreshed = await Project.get(project.id)
    assert refreshed.status == "ready"
    assert refreshed.latest_analysis_id == str(done.id)
    assert refreshed.code == "PRJ90"


async def test_reanalysis_is_a_new_version_and_keeps_the_previous(project):
    svc = service()
    first = await svc.run(str((await svc.create(project)).id))
    second = await svc.create(await Project.get(project.id))
    assert second.version == first.version + 1
    assert second.previous_analysis_id == str(first.id)
    await svc.run(str(second.id))
    assert await Analysis.get(first.id)
    assert await GraphNode.find(GraphNode.analysis_id == str(first.id)).count() > 0


async def test_failing_criterion_does_not_fail_the_analysis(project):
    handlers = full_handlers()
    original = handlers[DocSubOut]

    def flaky(messages):
        if "Sistematicidade" in messages[-1]["content"]:
            raise RuntimeError("model down")
        return original(messages)

    done = await service(FakeLLM(handlers | {DocSubOut: flaky})).run(str((await service().create(project)).id))
    stages = {s.name: s for s in done.stages}
    assert stages["SIS"].status == "falhou"
    assert stages["NOV"].status == "concluida"
    assert done.status == "concluida"
    assert done.suggestion is not None


async def test_extraction_failure_fails_the_analysis_and_marks_project(project, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("cannot read")

    monkeypatch.setattr("backend.analyses.orchestrator.extract_project", boom)
    svc = service()
    done = await svc.run(str((await svc.create(project)).id))
    stages = {s.name: s.status for s in done.stages}
    assert done.status == "falhou"
    assert stages["extracao"] == "falhou"
    assert stages["NOV"] == "nao_executada"
    assert (await Project.get(project.id)).status == "error"


async def test_unfinished_analyses_are_marked_interrupted_on_startup(project):
    svc = service()
    analysis = await svc.create(project)
    analysis.status = "rodando"
    await analysis.save()
    await AnalysisService.mark_interrupted()
    assert (await Analysis.get(analysis.id)).status == "falhou"


async def test_missing_model_fails_the_analysis_instead_of_leaving_it_pending(project):
    from backend.llm import LLMClient

    settings = Settings(_env_file=None, ollama_model="")
    svc = AnalysisService(LLMClient(settings), lambda: {}, settings, get_catalog())
    done = await svc.run(str((await svc.create(project)).id))
    assert done.status == "falhou"
    assert "OLLAMA_MODEL" in (done.error or "")
    assert done.versions.models["doc"] is None
    assert (await Project.get(project.id)).status == "error"


async def test_usage_counts_every_llm_call_and_survives_the_stage_saves(db):
    from collections import Counter

    from backend.analyses.models import Analysis
    from tests.factories import analysed_project

    _, analysis = await analysed_project()
    stored = await Analysis.get(analysis.id)
    expected = Counter(role for _, role, _ in analysis_llm_calls(analysis))
    assert expected["doc"] == 5
    assert {role: usage.calls for role, usage in stored.usage.roles.items()} == dict(expected)


def analysis_llm_calls(analysis):
    """The FakeLLM of the last analysed_project run records every call."""
    from tests import factories

    return factories.LAST_FAKE_LLM.calls
