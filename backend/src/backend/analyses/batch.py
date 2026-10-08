"""Batch processing (e.g. PRJ21–40) with a queue and a progress panel."""

import tempfile
from pathlib import Path

from beanie import PydanticObjectId

from backend.analyses.deps import start_analysis
from backend.analyses.models import Analysis, Batch
from backend.analyses.orchestrator import AnalysisService
from backend.analyses.schemas import BatchItem, BatchRead
from backend.projects.importer import IncomingFile, files_from_directory, find_project_dirs, project_code_from
from backend.projects.models import Project
from backend.projects.service import create_project

STATUSES = ("pendente", "rodando", "concluida", "falhou")


async def import_projects(groups: list[tuple[str, list[IncomingFile]]], owner_id: str, name: str,
                          service: AnalysisService, runner) -> Batch:
    batch = Batch(owner_id=owner_id, name=name)
    await batch.insert()
    projects = []
    for folder_name, files in groups:
        project = await create_project(owner_id, folder_name, files)
        projects.append(project)
        batch.project_ids.append(str(project.id))
    await batch.save()
    for project in projects:  # all projects exist before the first analysis starts
        analysis = await start_analysis(project, service, runner, batch_id=str(batch.id))
        batch.analysis_ids.append(str(analysis.id))
    await batch.save()
    return batch


def groups_from_directory(root: Path) -> list[tuple[str, list[IncomingFile]]]:
    return [(folder.name, files_from_directory(folder)) for folder in find_project_dirs(root)]


def groups_from_zip_files(files: list[IncomingFile]) -> list[tuple[str, list[IncomingFile]]]:
    """A zip with several project folders: written to a temporary folder and discovered by content."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for f in files:
            target = (root / (f"{f.top_folder}/{f.path}" if f.top_folder else f.path)).resolve()
            if root.resolve() not in target.parents:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.data)
        return groups_from_directory(root)


async def batch_panel(batch: Batch) -> BatchRead:
    items: list[BatchItem] = []
    counts = dict.fromkeys(STATUSES, 0)
    analyses = {str(a.id): a for a in await Analysis.find({"batch_id": str(batch.id)}).to_list()}
    for project_id in batch.project_ids:
        project = await Project.get(PydanticObjectId(project_id))
        analysis = next((a for a in analyses.values() if a.project_id == project_id), None)
        status = analysis.status if analysis else "pendente"
        counts[status] = counts.get(status, 0) + 1
        running = next((s.name for s in analysis.stages if s.status == "rodando"), None) if analysis else None
        items.append(
            BatchItem(
                project_id=project_id,
                project_name=project.name if project else "?",
                code=project.code if project else project_code_from(project.name if project else None),
                analysis_id=str(analysis.id) if analysis else None,
                status=status,
                suggested_class=analysis.suggestion.suggested_class if analysis and analysis.suggestion else None,
                inconsistent=analysis.suggestion.inconsistent if analysis and analysis.suggestion else None,
                total_s=analysis.total_s if analysis else None,
                current_stage=running,
            )
        )
    return BatchRead(id=str(batch.id), name=batch.name, created_at=batch.created_at, total=len(batch.project_ids),
                     counts=counts, items=items, errors=batch.errors)
