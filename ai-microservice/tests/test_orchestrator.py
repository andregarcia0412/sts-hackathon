from datetime import date

from ai_microservice.config import Settings
from ai_microservice.jobs import JobStatus, JobStore
from ai_microservice.modules.novelty.fronts import FrontAgent
from ai_microservice.modules.novelty.orchestrator import STEPS, NoveltyPipeline
from ai_microservice.modules.novelty.schemas import (
    DocComparison,
    EvidenceCitation,
    ProfileExtraction,
    QueryPlan,
    RuleJudgement,
)
from ai_microservice.rules import RuleStatus
from tests.factories import make_profile
from tests.test_fronts import COMPARISON, FakeProvider, hit
from tests.fakes import FakeLLM

DOSSIE = "PRJ21 | X\nEquipe: Y | Recorte de 32 semanas | Corte: 2025-08-18\nContexto..."


class ExplodingProvider(FakeProvider):
    async def search(self, query, before, limit):
        raise RuntimeError("unused")


def make_pipeline(broken_front: str | None = None, **profile_overrides) -> tuple[NoveltyPipeline, JobStore]:
    extraction = ProfileExtraction(
        **make_profile(**profile_overrides).model_dump(exclude={"data_referencia", "data_inicio_origem"})
    )
    llm = FakeLLM(
        {
            ProfileExtraction: lambda _: extraction,
            QueryPlan: lambda _: QueryPlan(queries=["bulkhead pattern"]),
            DocComparison: lambda _: COMPARISON,
            RuleJudgement: lambda _: RuleJudgement(
                status=RuleStatus.NAO_ENQUADRA,
                resumo="já existia",
                evidencias=[EvidenceCitation(fonte_id="lit-1", justificativa="descreve o padrão")],
            ),
        }
    )
    store = JobStore()
    pipeline = NoveltyPipeline(llm, Settings(_env_file=None, ollama_model="m"), store)

    def build_agents(http):
        agents = []
        for frente in ("literatura", "patentes", "mercado"):
            provider = FakeProvider({"bulkhead pattern": [hit(f"{frente[:3]}-1", date(2019, 1, 1))]})
            agent = FrontAgent(frente, provider, llm, queries=1, results_per_query=5, max_docs=5)
            if frente == broken_front:
                agent.run = _raise
            agents.append(agent)
        return agents

    pipeline.build_agents = build_agents
    return pipeline, store


async def _raise(profile):
    raise RuntimeError("quota exceeded")


async def test_pipeline_produces_full_report():
    pipeline, store = make_pipeline()
    job = store.create("novelty", STEPS)
    await pipeline.run(job.job_id, DOSSIE, None, None)

    job = store.get(job.job_id)
    assert job.status == JobStatus.DONE, job.error
    assert all(state == "done" for state in job.progress.values())
    report = job.result
    assert report.perfil.data_referencia == date(2025, 1, 6)
    assert len(report.regras) == 8
    assert {doc.frente for doc in report.fontes} == {"literatura", "patentes", "mercado"}
    assert report.modelos == {"extraction": "fake-extraction", "search": "fake-search", "judge": "fake-judge"}
    w3 = next(v for v in report.regras if v.id == "NOV-W3")
    assert w3.status == RuleStatus.NAO_ENQUADRA and w3.evidencias[0].fonte_id == "lit-1"


async def test_failed_front_is_reported_without_failing_the_job():
    pipeline, store = make_pipeline(broken_front="patentes")
    job = store.create("novelty", STEPS)
    await pipeline.run(job.job_id, DOSSIE, None, None)

    job = store.get(job.job_id)
    assert job.status == JobStatus.DONE
    assert job.progress["patentes"] == "failed"
    w2 = next(v for v in job.result.regras if v.id == "NOV-W2")
    assert w2.status == RuleStatus.NAO_ENQUADRA and "patentes" in w2.resumo
    assert any(entry.erro and "quota exceeded" in entry.erro for entry in job.result.log_busca)


async def test_missing_start_date_fails_the_job_with_clear_message():
    pipeline, store = make_pipeline(corte=None, recorte_semanas=None)
    job = store.create("novelty", STEPS)
    await pipeline.run(job.job_id, "dossiê sem cabeçalho", None, None)

    job = store.get(job.job_id)
    assert job.status == JobStatus.FAILED
    assert "data_inicio" in job.error
    assert job.progress["extracao"] == "failed"
