"""Module 4: who calls whom, in which order, and the per-stage status the front-end polls."""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from backend.analyses.models import Analysis, AnalysisVersions, CanonicalRecord, Stage
from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.config import LLM_ROLES, Settings
from backend.criteria.agent import CriteriaRunner
from backend.errors import safe_error_message
from backend.extraction.pipeline import extract_project
from backend.extraction.schema import SCHEMA_VERSION, CanonicalProject
from backend.graph.builder import build_graph
from backend.graph.classify import classify
from backend.graph.queries import save_graph
from backend.graph.scoring import score_criterion, score_rule
from backend.graph.states import judge_state, numeric_record_in
from backend.llm import LLM
from backend.llm.prompts import prompt_hashes
from backend.projects.importer import IncomingFile
from backend.projects.models import Project
from backend.report.service import generate_report
from backend.search.base import SearchProvider
from backend.storage import read_file

logger = logging.getLogger(__name__)

EXTRACTION, GRAPH, REPORT = "extracao", "grafo", "parecer"
STAGES: tuple[str, ...] = (EXTRACTION, "NOV", "SIS", "REP", "CRI", "INC", GRAPH, REPORT)
ProviderFactory = Callable[[], dict[str, SearchProvider]]


class AnalysisService:
    def __init__(self, llm: LLM, providers: ProviderFactory, settings: Settings, catalog: Catalog) -> None:
        self.llm, self.providers, self.settings, self.catalog = llm, providers, settings, catalog
        self._lock = asyncio.Lock()

    async def create(self, project: Project, batch_id: str | None = None) -> Analysis:
        previous = await Analysis.find(Analysis.project_id == str(project.id)).sort(-Analysis.version).first_or_none()
        analysis = Analysis(
            project_id=str(project.id),
            owner_id=project.owner_id,
            version=(previous.version + 1) if previous else 1,
            previous_analysis_id=str(previous.id) if previous else None,
            batch_id=batch_id,
            stages=[Stage(name=name) for name in STAGES],
        )
        await analysis.insert()
        project.latest_analysis_id = str(analysis.id)
        project.status = "processing"
        await project.save()
        return analysis

    @staticmethod
    async def mark_interrupted() -> None:
        """Analyses left running by a restart are failures, never silently resumed."""
        for analysis in await Analysis.find({"status": {"$in": ["pendente", "rodando"]}}).to_list():
            analysis.status = "falhou"
            analysis.error = "interrompida: o servidor reiniciou durante o processamento"
            for stage in analysis.stages:
                if stage.status in ("pendente", "rodando"):
                    stage.status = "nao_executada"
            await analysis.save()
            if project := await Project.get(analysis.project_id):
                if project.latest_analysis_id == str(analysis.id):
                    project.status = "error"
                    await project.save()

    def _models(self) -> dict[str, str | None]:
        models: dict[str, str | None] = {}
        for role in LLM_ROLES:
            try:
                models[role] = self.llm.model_for(role)
            except RuntimeError:
                models[role] = None
        return models

    async def _set_stage(self, analysis: Analysis, name: str, status: str, error: str | None = None) -> None:
        # Mutate and save under the lock: a concurrent save would write back a stale snapshot.
        async with self._lock:
            stage = analysis.stage(name)
            moment = datetime.now(UTC)
            if status == "rodando":
                stage.started_at = moment
            else:
                stage.finished_at = moment
                if stage.started_at:
                    started = stage.started_at if stage.started_at.tzinfo else stage.started_at.replace(tzinfo=UTC)
                    stage.duration_s = round((moment - started).total_seconds(), 3)
            stage.status = status
            stage.error = error
            await analysis.save()

    async def _load_files(self, project: Project) -> list[IncomingFile]:
        return [
            IncomingFile(path=doc.file_name, data=await read_file(doc.gridfs_id), top_folder=project.code)
            for doc in project.active_documents()
        ]

    async def run(self, analysis_id: str) -> Analysis:
        analysis = await Analysis.get(analysis_id)
        project = await Project.get(analysis.project_id)
        started = time.monotonic()
        analysis.status, analysis.started_at = "rodando", datetime.now(UTC)
        models = self._models()
        analysis.versions = AnalysisVersions(
            schema_version=SCHEMA_VERSION,
            catalog_version=self.catalog.versao,
            models=models,
            file_hashes={doc.file_name: doc.sha256 for doc in project.active_documents()},
        )
        await analysis.save()
        try:
            missing = [role for role, model in models.items() if model is None]
            if missing:
                raise RuntimeError(f"OLLAMA_MODEL is not set in .env (roles without model: {', '.join(missing)})")
            canonical = await self._extract(analysis, project)
            if canonical is not None:
                await self._criteria_graph_report(analysis, canonical)
        except Exception as error:  # defensive: never leave an analysis "running"
            analysis.error = safe_error_message(error)
            analysis.status = "falhou"
            if analysis.stage(EXTRACTION).status == "pendente":
                analysis.stage(EXTRACTION).status, analysis.stage(EXTRACTION).error = "falhou", analysis.error
        analysis.versions.prompts = prompt_hashes()
        analysis.finished_at = datetime.now(UTC)
        analysis.total_s = round(time.monotonic() - started, 3)
        if analysis.status == "rodando":
            analysis.status = "concluida"
        for stage in analysis.stages:
            if stage.status in ("pendente", "rodando"):
                stage.status = "nao_executada"
        await analysis.save()
        project = await Project.get(analysis.project_id)
        if project.latest_analysis_id == str(analysis.id):
            project.status = "ready" if analysis.status == "concluida" else "error"
            await project.save()
        return analysis

    async def _extract(self, analysis: Analysis, project: Project) -> CanonicalProject | None:
        await self._set_stage(analysis, EXTRACTION, "rodando")
        try:
            canonical = await extract_project(
                self.llm, await self._load_files(project), code_hint=project.code,
                reference_date=analysis.reference_date_override,
            )
        except Exception as error:
            message = safe_error_message(error)
            analysis.status, analysis.error = "falhou", f"extração falhou: {message}"
            await self._set_stage(analysis, EXTRACTION, "falhou", message)
            return None
        await CanonicalRecord(analysis_id=str(analysis.id), canonical=canonical).insert()
        if not project.code and canonical.project_code != "PRJ":
            project.code = canonical.project_code
            await project.save()
        pending = [f.path for f in canonical.files if f.status != "reconhecido"]
        await self._set_stage(analysis, EXTRACTION, "concluida",
                              f"pendente de validação: {', '.join(pending)}" if pending else None)
        return canonical

    async def _criteria_graph_report(self, analysis: Analysis, canonical: CanonicalProject) -> None:
        runner = CriteriaRunner(
            self.llm, self.catalog, self.providers(),
            on_stage=lambda name, status, error=None: self._set_stage(analysis, name, status, error),
            queries_per_front=self.settings.web_queries_per_front,
            results_per_query=self.settings.web_results_per_query,
            fetch_per_front=self.settings.web_fetch_per_front,
            max_table_rows=self.settings.prompt_max_table_rows,
        )
        results = await runner.run_all(canonical)
        analysis.criteria = results

        await self._set_stage(analysis, GRAPH, "rodando")
        try:
            analysis.scores = {
                c: [score_rule(run, self.catalog.get(run.rule_id)) for run in result.rules] for c, result in results.items()
            }
            analysis.criterion_scores = {c: score_criterion(s) for c, s in analysis.scores.items()}
            numeric = numeric_record_in(results)
            judged = await asyncio.gather(
                *(judge_state(self.llm, self.catalog, results[c], numeric) for c in CRITERIA_ORDER)
            )
            analysis.states = dict(zip(CRITERIA_ORDER, judged, strict=True))
            analysis.suggestion = classify(analysis.states)
            nodes, edges = build_graph(str(analysis.id), canonical, self.catalog, results, analysis.scores,
                                       analysis.states, analysis.suggestion)
            await save_graph(str(analysis.id), nodes, edges)
        except Exception as error:
            await self._set_stage(analysis, GRAPH, "falhou", safe_error_message(error))
            analysis.status = "falhou"
            return
        await self._set_stage(analysis, GRAPH, "concluida")

        await self._set_stage(analysis, REPORT, "rodando")
        try:
            analysis.report = await generate_report(self.llm, self.catalog, analysis, canonical)
        except Exception as error:  # the report failing keeps the graph and the suggestion
            await self._set_stage(analysis, REPORT, "falhou", safe_error_message(error))
            return
        await self._set_stage(analysis, REPORT, "concluida")
