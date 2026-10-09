"""Module 4: who calls whom, in which order, and the per-stage status the front-end polls."""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from backend.analyses.models import Analysis, AnalysisVersions, CanonicalRecord, Stage
from backend.analyses.worker import is_orphan, worker_id
from backend.catalog.models import Catalog
from backend.checks.divergences import add_check_divergences
from backend.checks.runner import run_checks, with_check_fragments
from backend.config import LLM_ROLES, Settings
from backend.criteria.agent import CriteriaRunner
from backend.errors import safe_error_message
from backend.extraction.pipeline import extract_project
from backend.extraction.schema import SCHEMA_VERSION, CanonicalProject
from backend.graph.builder import build_graph
from backend.graph.judge import JudgeOptions, judge_and_classify
from backend.graph.queries import save_graph
from backend.llm import LLM
from backend.llm.prompts import prompt_hashes
from backend.llm.usage import current_usage, meter_scope
from backend.projects.importer import IncomingFile
from backend.projects.models import Project
from backend.report.service import generate_report
from backend.search.base import SearchProvider
from backend.storage import read_file

logger = logging.getLogger(__name__)

EXTRACTION, CHECKS, GRAPH, REPORT = "extracao", "checagens", "grafo", "parecer"
STAGES: tuple[str, ...] = (EXTRACTION, CHECKS, "NOV", "SIS", "REP", "CRI", "INC", GRAPH, REPORT)
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
            worker=worker_id(),  # the job runner is in-process: whoever creates it runs it
            heartbeat_at=datetime.now(UTC),
        )
        await analysis.insert()
        project.latest_analysis_id = str(analysis.id)
        project.status = "processing"
        await project.save()
        return analysis

    def stale_after_s(self) -> float:
        """A worker of another host silent for this long is gone (a stage can take this long on retries)."""
        return 2 * self.settings.ollama_timeout_s * (self.settings.ollama_retries + 1)

    async def mark_interrupted(self) -> None:
        """Analyses left running by a restart are failures, never silently resumed. Only those whose process is
        gone: a CLI benchmark running in another process (or the reloaded server's sibling) keeps its analyses."""
        for analysis in await Analysis.find({"status": {"$in": ["pendente", "rodando"]}}).to_list():
            if not is_orphan(analysis.worker, analysis.heartbeat_at, self.stale_after_s()):
                continue
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

    def models_by_role(self) -> dict[str, str | None]:
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
            analysis.heartbeat_at = moment
            self._snapshot_usage(analysis)
            await analysis.save()

    @staticmethod
    def _snapshot_usage(analysis: Analysis) -> None:
        """A copy of the live meter: `save()` merges the stored document back into nested objects,
        which would wipe counters mutated in place by the calls running in parallel."""
        if (meter := current_usage()) is not None:
            analysis.usage = meter.model_copy(deep=True)

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
        analysis.worker, analysis.heartbeat_at = worker_id(), analysis.started_at
        models = self.models_by_role()
        analysis.versions = AnalysisVersions(
            schema_version=SCHEMA_VERSION,
            catalog_version=self.catalog.versao,
            models=models,
            file_hashes={doc.file_name: doc.sha256 for doc in project.active_documents()},
        )
        await analysis.save()
        with meter_scope() as usage:
            try:
                missing = [role for role, model in models.items() if model is None]
                if missing:
                    raise RuntimeError(f"OLLAMA_MODEL is not set in .env (roles without model: {', '.join(missing)})")
                canonical = await self._extract(analysis, project)
                if canonical is not None:
                    canonical = await self._checks(analysis, canonical)
                    await self._criteria_graph_report(analysis, canonical)
            except Exception as error:  # defensive: never leave an analysis "running"
                analysis.error = safe_error_message(error)
                analysis.status = "falhou"
                if analysis.stage(EXTRACTION).status == "pendente":
                    analysis.stage(EXTRACTION).status, analysis.stage(EXTRACTION).error = "falhou", analysis.error
        analysis.usage = usage.model_copy(deep=True)
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
        for extracted in canonical.files:
            analysis.mapping_sources[extracted.mapping_source] = analysis.mapping_sources.get(extracted.mapping_source, 0) + 1
        if not project.code and canonical.project_code != "PRJ":
            project.code = canonical.project_code
            await project.save()
        pending = [f.path for f in canonical.files if f.status != "reconhecido"]
        await self._set_stage(analysis, EXTRACTION, "concluida",
                              f"pendente de validação: {', '.join(pending)}" if pending else None)
        return canonical

    async def _checks(self, analysis: Analysis, canonical: CanonicalProject) -> CanonicalProject:
        """Deterministic checks (zero tokens): facts and citable fragments for the criterion agents."""
        await self._set_stage(analysis, CHECKS, "rodando")
        analysis.checks = run_checks(canonical)
        analysis.versions.checks_version = analysis.checks.version
        failed = [c for c, r in analysis.checks.results.items() if r.status == "falhou"]
        canonical = with_check_fragments(canonical, analysis.checks)
        if record := await CanonicalRecord.find_one(CanonicalRecord.analysis_id == str(analysis.id)):
            record.canonical = canonical  # the check fragments are citable: keep them with the canonical
            await record.save()
        await self._set_stage(analysis, CHECKS, "concluida", f"checagens que falharam: {', '.join(failed)}" if failed else None)
        return canonical

    async def _criteria_graph_report(self, analysis: Analysis, canonical: CanonicalProject) -> None:
        runner = CriteriaRunner(
            self.llm, self.catalog, self.providers(),
            on_stage=lambda name, status, error=None: self._set_stage(analysis, name, status, error),
            queries_per_front=self.settings.web_queries_per_front,
            results_per_query=self.settings.web_results_per_query,
            fetch_per_front=self.settings.web_fetch_per_front,
            max_table_rows=self.settings.prompt_max_table_rows,
            doc_pitfalls=self.settings.doc_handbook_pitfalls,
        )
        results = await runner.run_all(canonical)
        if analysis.checks:
            add_check_divergences(results, canonical, analysis.checks)
        analysis.criteria = results

        await self._set_stage(analysis, GRAPH, "rodando")
        try:
            options = JudgeOptions.from_settings(self.settings)
            analysis.versions.judge = options.model_dump()
            outcome = await judge_and_classify(self.llm, self.catalog, results, options, analysis.checks)
            analysis.scores, analysis.criterion_scores = outcome.scores, outcome.criterion_scores
            analysis.states, analysis.suggestion = outcome.states, outcome.suggestion
            analysis.consistency = outcome.consistency
            nodes, edges = build_graph(str(analysis.id), canonical, self.catalog, results, analysis.scores,
                                       analysis.states, analysis.suggestion, analysis.consistency, analysis.checks)
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
