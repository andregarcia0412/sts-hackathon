import mimetypes

from beanie import PydanticObjectId
from bson.errors import InvalidId

from backend.projects.importer import IncomingFile, project_code_from
from backend.projects.models import Project, ProjectFile, now
from backend.storage import store_file


def guess_mime(path: str) -> str:
    if path.endswith(".md"):
        return "text/markdown"
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


async def _store(project: Project, incoming: IncomingFile) -> ProjectFile:
    stored = await store_file(incoming.path, incoming.data, {"project_id": str(project.id), "path": incoming.path})
    return ProjectFile(
        file_name=incoming.path,
        mime_type=guess_mime(incoming.path),
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        gridfs_id=stored.gridfs_id,
    )


async def create_project(
    owner_id: str,
    name: str,
    files: list[IncomingFile],
    company: str | None = None,
    free_text: str | None = None,
) -> Project:
    code = project_code_from(name, *(f.top_folder for f in files))
    project = Project(owner_id=owner_id, name=name.strip(), company=company, free_text=free_text, code=code)
    await project.insert()
    project.documents = [await _store(project, incoming) for incoming in files]
    await project.save()
    return project


async def add_documents(project: Project, files: list[IncomingFile]) -> Project:
    """New version of a file supersedes the old one (kept, never deleted)."""
    for incoming in files:
        new_file = await _store(project, incoming)
        for old in project.active_documents():
            if old.file_name == incoming.path:
                old.superseded_at = now()
                old.superseded_by = new_file.id
        project.documents.append(new_file)
    await project.save()
    return project


async def get_owned_project(project_id: str, owner_id: str) -> Project | None:
    try:
        object_id = PydanticObjectId(project_id)
    except (InvalidId, TypeError):
        return None
    project = await Project.get(object_id)
    return project if project and project.owner_id == owner_id else None
