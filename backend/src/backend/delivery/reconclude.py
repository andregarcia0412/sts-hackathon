"""Re-conclude a delivery (or any benchmark): a new version of each finished analysis that re-runs only the
conclusion with the current judge, graph and report — a few calls per project instead of a full run."""

from beanie import PydanticObjectId

from backend.analyses.models import Batch
from backend.benchmark.models import Benchmark, BenchmarkRun
from backend.benchmark.service import refresh
from backend.delivery.export import latest_analyses
from backend.llm.prompts import prompt_hashes
from backend.projects.models import Project


async def reconclude_benchmark(source: Benchmark, service, runner, name: str | None = None) -> Benchmark:
    analyses, _ = await latest_analyses(source)
    sets = {run.code: run.set for run in source.runs}
    benchmark = Benchmark(owner_id=source.owner_id, name=name or f"{source.name} · reconcluído",
                          expected=source.expected,
                          config=source.config.model_copy(update={
                              "models": service.models_by_role(), "catalog_version": service.catalog.versao,
                              "prompts": prompt_hashes(), "resumed_from": None, "reconcluded_from": str(source.id)}))
    await benchmark.insert()
    batch = Batch(owner_id=source.owner_id, name=benchmark.name, benchmark_id=str(benchmark.id))
    await batch.insert()
    benchmark.batch_ids.append(str(batch.id))
    for code, analysis in sorted(analyses.items()):
        project = await Project.get(PydanticObjectId(analysis.project_id))
        new = await service.create(project, batch_id=str(batch.id), reconcluded_from=str(analysis.id))
        batch.project_ids.append(str(project.id))
        batch.analysis_ids.append(str(new.id))
        benchmark.runs.append(BenchmarkRun(set=sets.get(code, "analise"), code=code, project_id=str(project.id),
                                           analysis_id=str(new.id), repeat=1))
    await batch.save()
    await benchmark.save()
    for run in benchmark.runs:
        analysis_id = run.analysis_id
        await runner.submit(lambda analysis_id=analysis_id: service.run(analysis_id))
    return await refresh(await Benchmark.get(benchmark.id), service.catalog)
