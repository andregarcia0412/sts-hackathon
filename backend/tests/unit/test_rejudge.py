from backend.analyses.models import Analysis
from backend.benchmark.models import Benchmark, BenchmarkConfig, BenchmarkRun
from backend.benchmark.reference import ExpectedCase
from backend.benchmark.rejudge import create_rejudge, run_rejudge
from backend.benchmark.service import progress, refresh
from backend.catalog.loader import get_catalog
from backend.graph.judge import JudgeOptions
from backend.graph.states import StateJudgeOut
from tests.factories import ELIGIBLE_STATES, analysed_project, fake_state
from tests.fakes import FakeLLM

ROUTINE = {"NOV": "NÃO DEMONSTRADA", "CRI": "NÃO DEMONSTRADA", "INC": "NÃO CARACTERIZADA",
           "SIS": "DOCUMENTADA COMO ACEITE", "REP": "DOCUMENTADA PARA A CONFIGURAÇÃO"}


async def _source(*analyses: Analysis) -> Benchmark:
    runs = [BenchmarkRun(set="historico", code=f"PRJ9{i}", project_id=a.project_id, analysis_id=str(a.id), repeat=1)
            for i, a in enumerate(analyses)]
    expected = {"PRJ90": ExpectedCase(code="PRJ90", source="oficial", expected_class="not_eligible")}
    source = Benchmark(owner_id="owner-1", name="origem", runs=runs, expected=expected,
                       config=BenchmarkConfig(models={"judge": "old"}, catalog_version="old"))
    await source.insert()
    return source


async def _rejudge(source, llm, repeats=1, projects=None):
    options = JudgeOptions()
    benchmark = await create_rejudge(source, "owner-1", {"judge": "fake-judge"}, get_catalog(), options,
                                     projects=projects, repeats=repeats)
    return await run_rejudge(benchmark, llm, get_catalog(), options)


async def test_rejudge_creates_a_new_benchmark_and_never_writes_the_source_analysis(db):
    _, analysis = await analysed_project()
    assert analysis.suggestion.suggested_class == "eligible"
    source = await _source(analysis)

    llm = FakeLLM({StateJudgeOut: fake_state(ROUTINE)})
    benchmark = await _rejudge(source, llm)

    assert benchmark.status == "concluido" and benchmark.id != source.id
    assert benchmark.config.rejudged_from == str(source.id)
    assert benchmark.config.models == {"judge": "fake-judge"}
    [snap] = benchmark.snapshots
    assert snap.rejudged and snap.analysis_id == str(analysis.id)
    assert snap.suggested_class == "not_eligible" and snap.states["INC"] == "NÃO CARACTERIZADA"
    assert benchmark.metrics.accuracy["oficial"].class_hits == 1

    stored = await Analysis.get(analysis.id)
    assert stored.suggestion.suggested_class == "eligible"
    assert stored.states["INC"].state == ELIGIBLE_STATES["INC"]

    # only the judge ran: one call per criterion
    assert [role for _, role, _ in llm.calls] == ["judge"] * 5
    assert snap.usage.roles["judge"].calls == 5


async def test_rejudge_uses_only_finished_analyses(db):
    _, done = await analysed_project()
    _, failed = await analysed_project()
    failed.status = "falhou"
    await failed.save()
    source = await _source(done, failed)
    source.status = "rodando"  # a source stuck in "rodando" still works
    await source.save()

    benchmark = await _rejudge(source, FakeLLM({StateJudgeOut: fake_state()}))
    assert [run.analysis_id for run in benchmark.runs] == [str(done.id)]
    assert progress(benchmark, {}) == {"pendente": 0, "rodando": 0, "concluida": 1, "falhou": 0}


async def test_rejudge_repeats_measure_the_judge_variance(db):
    _, analysis = await analysed_project()
    benchmark = await _rejudge(await _source(analysis), FakeLLM({StateJudgeOut: fake_state()}), repeats=2)
    assert sorted(s.repeat for s in benchmark.snapshots) == [1, 2]
    assert benchmark.metrics.determinism.class_agreement == 1.0


async def test_refresh_never_recomputes_a_rejudge_from_the_source_analyses(db):
    _, analysis = await analysed_project()
    source = await _source(analysis)
    benchmark = await create_rejudge(source, "owner-1", {}, get_catalog(), JudgeOptions())
    assert (await refresh(benchmark, get_catalog())).status == "rodando"
    assert progress(benchmark, {})["pendente"] == 1


async def test_rejudge_filters_projects(db):
    _, first = await analysed_project()
    _, second = await analysed_project()
    benchmark = await _rejudge(await _source(first, second), FakeLLM({StateJudgeOut: fake_state()}),
                               projects=["prj91"])
    assert [s.code for s in benchmark.snapshots] == ["PRJ91"]
