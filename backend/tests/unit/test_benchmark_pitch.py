import re

from backend.benchmark.metrics import per_model
from backend.benchmark.models import Benchmark, BenchmarkConfig, RunSnapshot
from backend.benchmark.report_html import report_html
from backend.benchmark.service import snapshot_of
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.llm.calls import CallRecord, LLMCall, summarize
from tests.factories import analysed_project


async def test_every_llm_call_is_logged_with_its_stage_and_model_and_nothing_else(db):
    _, analysis = await analysed_project()
    from tests import factories

    calls = await LLMCall.find(LLMCall.analysis_id == str(analysis.id)).to_list()
    assert len(calls) == len(factories.LAST_FAKE_LLM.calls)
    stages = {c.stage for c in calls}
    assert {"extracao", "NOV", "SIS", "REP", "CRI", "INC", "grafo", "parecer"} <= stages
    doc = next(c for c in calls if c.schema_name == "DocSubOut" and c.stage == "SIS")
    assert (doc.role, doc.model) == ("doc", "fake-doc")
    assert not {"messages", "content", "prompt", "answer"} & set(LLMCall.model_fields)  # numbers only
    assert analysis.calls.by_model["fake-doc"].calls == 5
    assert sum(u.calls for u in analysis.calls.by_model.values()) == len(calls)


def test_two_roles_on_the_same_model_add_up_and_cost_needs_a_configured_price():
    summary = summarize([CallRecord(stage="NOV", role="doc", model="m1", prompt_tokens=1000, completion_tokens=10),
                         CallRecord(stage="grafo", role="judge", model="m1", prompt_tokens=500, completion_tokens=5),
                         CallRecord(stage="grafo", role="judge", model="m1", attempt=2, ok=False),
                         CallRecord(stage="NOV", role="search", model="m2", prompt_tokens=10, completion_tokens=1)])
    run = RunSnapshot(set="historico", code="PRJ90", repeat=1, analysis_id="a", status="concluida", calls=summary)
    models, stages, cost = per_model([run], {})
    m1 = models["m1"]
    assert (m1.calls, m1.failures, m1.retries, m1.prompt_tokens) == (2, 1, 1, 1500)
    assert m1.roles == {"doc": 1, "judge": 1} and m1.stages == {"NOV": 1, "grafo": 1}
    assert stages["grafo"].calls == 1
    assert cost.total is None and m1.cost is None and cost.unpriced_models == ["m1", "m2"]  # never invented
    models, _, cost = per_model([run], Settings(_env_file=None, model_prices="m1=1/2;m2=3").prices())
    assert models["m1"].cost == round((1500 * 1 + 15 * 2) / 1e6, 6) and cost.total is not None


async def test_report_is_self_contained_and_says_where_every_number_comes_from(db):
    _, analysis = await analysed_project()
    from backend.benchmark.metrics import compute
    from backend.benchmark.models import BenchmarkRun

    run = BenchmarkRun(set="historico", code="PRJ90", project_id=analysis.project_id, analysis_id=str(analysis.id),
                       repeat=1)
    snap = snapshot_of(run, analysis)
    benchmark = Benchmark(owner_id="o", name="pitch", runs=[run], snapshots=[snap],
                          config=BenchmarkConfig(models={"doc": "fake-doc"}, catalog_version="v1"))
    benchmark.metrics = compute([snap], {}, get_catalog(),
                                Settings(_env_file=None, manual_analysis_minutes=240, manual_analysis_source=None))
    await benchmark.insert()
    html = report_html(benchmark)
    assert not re.search(r"(?:src|href)\s*=\s*[\"']?(?:https?:)?//", html)  # opens offline
    assert "fake-doc" in html and str(benchmark.id) in html and "catálogo v1" in html
    assert benchmark.metrics.time_vs_manual is None  # no source, no comparison
    assert benchmark.metrics.defensibility.with_source == 1.0
