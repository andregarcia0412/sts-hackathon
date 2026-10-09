"""Spec 13 — `backend-export-frontend`: static JSON export of what the front-end consumes.

Reads Mongo and writes route-shaped payloads (`frontend-static/`) so the hifi front can run
without the backend. Reuses the projection the routes use (never a parallel mapping).
"""

import hashlib
import json
import re

import pytest

from backend.analyses.jobs import InlineRunner
from backend.analyses.deps import start_analysis
from backend.analyses.models import Analysis
from backend.analyses.orchestrator import AnalysisService
from backend.analyses.schemas import GraphRead
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.frontend_api.exporter import ExportError, export_frontend
from backend.projects.models import Project
from backend.projects.importer import IncomingFile
from backend.projects.service import create_project
from backend.users.models import User
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM

SETTINGS = Settings(_env_file=None, ollama_model="m")


def write_cases(root, codes=("PRJ91", "PRJ92")):
    for code in codes:
        for f in synthetic_package():
            target = root / code / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.data.replace(b"PRJ90", code.encode()))
    return root


async def analyse(root, owner: str):
    """Creates the projects and runs the pipeline with the fakes, like the delivery test."""
    project_ids = []
    for code in sorted(p.name for p in root.iterdir() if p.is_dir()):
        files = [IncomingFile(path=f.path, data=f.data.replace(b"PRJ90", code.encode()))
                 for f in synthetic_package()]
        project = await create_project(owner, code, files)
        project_ids.append(str(project.id))
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, SETTINGS, get_catalog())
    runner = InlineRunner()
    for pid in project_ids:
        await start_analysis(await Project.get(pid), service, runner)
    await runner.wait_all()
    return project_ids


@pytest.fixture
async def analysed(db, tmp_path):
    owner = await User(email="ana@sts.com", name="Ana", password_hash="x").insert()
    folder = write_cases(tmp_path / "casos")
    project_ids = await analyse(folder, str(owner.id))
    return folder, project_ids, tmp_path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


async def test_export_writes_route_payloads_for_synthetic_project(analysed):
    _, project_ids, tmp_path = analysed
    out = tmp_path / "frontend-static"
    result = await export_frontend(out)
    assert result.ok and len(result.projects) == 2

    users = read_json(out / "users.json")
    assert users and all(set(u) == {"id", "name", "email"} for u in users)
    assert users[0]["email"] == "ana@sts.com"

    projects = read_json(out / "projects.json")
    ids = [p["id"] for p in projects["items"]]
    assert sorted(ids) == sorted(project_ids)
    assert projects["total"] == 2 and projects["page"] == 1
    assert projects["statusCounts"]  # every status counted

    for pid in project_ids:
        folder = out / pid
        project = read_json(folder / "project.json")
        assert project["id"] == pid and project["status"] == "ready"
        analyses = read_json(folder / "analyses.json")
        assert isinstance(analyses, list) and analyses[0]["criteria"]  # hifi tree with criteria
        assert read_json(folder / "decisions.json") == []
        graph = read_json(folder / "analysis" / analyses[0]["id"] / "graph.json")
        assert graph["analysisId"] == analyses[0]["id"] and graph["nodes"] and graph["edges"]
        status = read_json(folder / "analysis" / analyses[0]["id"] / "status.json")
        assert status["status"] == "concluida" and status["stages"]
        report = read_json(folder / "analysis" / analyses[0]["id"] / "report.json")
        assert report and report != {}


async def test_graph_and_analyses_validate_against_frontend_schemas(analysed):
    _, project_ids, tmp_path = analysed
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    from backend.frontend_api import schemas as fe

    for pid in project_ids:
        analyses = read_json(out / pid / "analyses.json")
        fe.Analysis.model_validate(analyses[0])  # fail fast: the export is the contract
        graph = read_json(out / pid / "analysis" / analyses[0]["id"] / "graph.json")
        GraphRead.model_validate(graph)


async def test_projects_without_analysis_export_with_null_analyses(analysed, db, tmp_path):
    _, project_ids, _ = analysed
    owner = await User.find_one()
    extra = await Project(owner_id=str(owner.id), name="Sem análise",
                          documents=[], status="processing").insert()
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    assert read_json(out / "projects.json")["total"] == 3
    folder = out / str(extra.id)
    assert read_json(folder / "analyses.json") is None
    assert not (folder / "analysis").exists()
    summary = next(p for p in read_json(out / "projects.json")["items"] if p["id"] == str(extra.id))
    assert summary["scoreSummary"] is None and summary["status"] == "processing"


async def test_benchmark_projects_are_hidden(analysed, db, tmp_path):
    _, _, _ = analysed
    owner = (await User.find_one()).id
    hidden = await Project(owner_id=str(owner), name="Do benchmark", documents=[], status="ready",
                           benchmark_id="bm-1").insert()
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    ids = [p["id"] for p in read_json(out / "projects.json")["items"]]
    assert str(hidden.id) not in ids and not (out / str(hidden.id)).exists()


async def test_failed_report_stage_omits_report_json(analysed, db, tmp_path):
    _, project_ids, _ = analysed
    analysis = await Analysis.find_one(Analysis.project_id == project_ids[0])
    analysis.report = None
    await analysis.save()
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    folder = out / project_ids[0] / "analysis" / str(analysis.id)
    assert (folder / "status.json").is_file()  # status still there
    assert not (folder / "report.json").exists()  # never a phantom report


async def test_manifest_has_counts_and_sha256(analysed, tmp_path):
    _, project_ids, _ = analysed
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    manifest = read_json(out / "manifest.json")
    assert manifest["geradoEm"]
    assert manifest["projects"] == 2
    assert manifest["routes"]["GET /projects/{id}"] == 2
    assert manifest["routes"]["GET /analyses/{id}/graph"] == 2
    assert manifest["catalogVersion"] == get_catalog().versao
    assert manifest["models"]
    files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"}
    assert manifest["files"] == files


async def test_owner_and_project_filters(analysed, db, tmp_path):
    _, project_ids, _ = analysed
    other = await User(email="bruno@sts.com", name="Bruno", password_hash="x").insert()
    lonely = await Project(owner_id=str(other.id), name="Só do Bruno", documents=[], status="ready").insert()
    out = tmp_path / "frontend-static"

    only_owner = await export_frontend(out / "owner", owner=str((await User.find_one(User.email == "ana@sts.com")).id))
    assert [p.id for p in only_owner.projects] == project_ids and not (out / "owner" / str(lonely.id)).exists()

    only_project = await export_frontend(out / "one", project=project_ids[0])
    items = read_json(out / "one" / "projects.json")["items"]
    assert [p["id"] for p in items] == [project_ids[0]] and (out / "one" / project_ids[1]).exists() is False


async def test_users_json_has_no_password_hash(analysed, tmp_path):
    out = tmp_path / "frontend-static"
    await export_frontend(out)
    raw = (out / "users.json").read_text(encoding="utf-8")
    assert not re.search(r"password_hash|argon2|\$argon2", raw)
    for p in out.rglob("*.json"):
        assert "OLLAMA_API_KEY" not in p.read_text(encoding="utf-8")


async def test_invalid_payload_fails_fast_with_the_file_path(analysed, db, tmp_path, monkeypatch):
    from backend.frontend_api import exporter

    async def broken(*args, **kwargs):  # a corrupted projection must never reach a JSON file
        return "NÃO SOU UMA ANÁLISE"

    monkeypatch.setattr(exporter, "_analysis_view", broken)
    with pytest.raises(ExportError) as error:
        await export_frontend(tmp_path / "broken")
    assert "analyses.json" in str(error.value)