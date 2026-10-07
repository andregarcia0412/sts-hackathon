import asyncio
from datetime import UTC, date, datetime

import httpx

from ai_microservice.config import Settings
from ai_microservice.errors import safe_error_message
from ai_microservice.jobs import JobStore
from ai_microservice.llm import LLMClient
from ai_microservice.modules.novelty.evaluator import evaluate_rules
from ai_microservice.modules.novelty.fronts import FrontAgent
from ai_microservice.modules.novelty.profile import extract_profile
from ai_microservice.modules.novelty.rules import NOVELTY_WEB_RULES
from ai_microservice.modules.novelty.schemas import Front, FrontResult, NoveltyReport, SearchLogEntry
from ai_microservice.search.ollama_web import OllamaWebProvider
from ai_microservice.search.openalex import OpenAlexProvider

JOB_KIND = "novelty"
STEPS = ["extracao", "literatura", "patentes", "mercado", "regras"]
OPENALEX_TIMEOUT_S = 30


class NoveltyPipeline:
    def __init__(self, llm: LLMClient, settings: Settings, store: JobStore) -> None:
        self.llm = llm
        self.settings = settings
        self.store = store

    def build_agents(self, http: httpx.AsyncClient) -> list[FrontAgent]:
        providers = {
            "literatura": OpenAlexProvider(http, self.settings.openalex_api_key, self.settings.openalex_mailto),
            "patentes": OllamaWebProvider(self.llm, name="google_patents", site="patents.google.com"),
            "mercado": OllamaWebProvider(self.llm, name="ollama_web_search"),
        }
        return [
            FrontAgent(
                frente=frente,
                provider=provider,
                llm=self.llm,
                queries=self.settings.novelty_queries_per_front,
                results_per_query=self.settings.novelty_results_per_query,
                max_docs=self.settings.novelty_fetch_per_front,
            )
            for frente, provider in providers.items()
        ]

    async def run(self, job_id: str, dossie: str, entrevista: str | None, data_inicio: date | None) -> None:
        try:
            self.store.finish(job_id, await self._run(job_id, dossie, entrevista, data_inicio))
        except Exception as error:
            self.store.fail(job_id, safe_error_message(error))

    async def _run(self, job_id: str, dossie: str, entrevista: str | None, data_inicio: date | None) -> NoveltyReport:
        self.store.set_step(job_id, "extracao", "running")
        profile = await extract_profile(self.llm, dossie, entrevista, data_inicio)
        self.store.set_step(job_id, "extracao", "done")

        async with httpx.AsyncClient(timeout=OPENALEX_TIMEOUT_S) as http:
            fronts = await asyncio.gather(*(self._run_front(job_id, agent, profile) for agent in self.build_agents(http)))

        self.store.set_step(job_id, "regras", "running")
        verdicts = await evaluate_rules(self.llm, NOVELTY_WEB_RULES, profile, fronts)
        self.store.set_step(job_id, "regras", "done")

        return NoveltyReport(
            perfil=profile,
            regras=verdicts,
            fontes=[doc for front in fronts for doc in front.fontes],
            log_busca=[entry for front in fronts for entry in front.log],
            modelos={role: self.llm.model_for(role) for role in ("extraction", "search", "judge")},
        )

    async def _run_front(self, job_id: str, agent: FrontAgent, profile) -> FrontResult:
        self.store.set_step(job_id, agent.frente, "running")
        try:
            result = await agent.run(profile)
        except Exception as error:  # uma frente que falha vira registro no log (e NOV-W2 aponta a lacuna)
            self.store.set_step(job_id, agent.frente, "failed")
            return self._failed_front(agent, error)
        self.store.set_step(job_id, agent.frente, "done")
        return result

    @staticmethod
    def _failed_front(agent: FrontAgent, error: Exception) -> FrontResult:
        frente: Front = agent.frente
        entry = SearchLogEntry(
            frente=frente,
            base=agent.provider.name,
            query="",
            executado_em=datetime.now(UTC),
            erro=f"frente interrompida: {safe_error_message(error)}",
        )
        return FrontResult(frente=frente, fontes=[], log=[entry])
