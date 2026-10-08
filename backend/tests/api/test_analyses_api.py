import io
import zipfile

import pytest

from backend.config import settings
from tests.conftest import package_upload
from tests.factories import synthetic_package


def create(client, headers):
    return client.post("/projects", data={"name": "PRJ90 fila"}, files=package_upload(), headers=headers).json()


def test_upload_starts_analysis_and_status_is_polled(client, auth_headers, fake_pipeline):
    project = create(client, auth_headers)
    assert project["latestAnalysisId"]
    status = client.get(f"/analyses/{project['latestAnalysisId']}/status", headers=auth_headers).json()
    assert status["status"] == "concluida"
    assert [s["name"] for s in status["stages"]][:2] == ["extracao", "NOV"]
    assert all({"status", "startedAt", "finishedAt", "durationS"} <= set(s) for s in status["stages"])
    assert status["suggestedClass"] == "eligible"
    assert status["versions"]["catalogVersion"]
    assert client.get(f"/projects/{project['id']}", headers=auth_headers).json()["status"] == "ready"


def test_reanalysis_creates_new_version(client, auth_headers, fake_pipeline):
    project = create(client, auth_headers)
    second = client.post(f"/projects/{project['id']}/analyses", headers=auth_headers).json()
    assert second["version"] == 2
    history = client.get(f"/projects/{project['id']}/analyses/history", headers=auth_headers).json()
    assert [a["version"] for a in history] == [2, 1]


def test_adding_a_document_triggers_reanalysis(client, auth_headers, fake_pipeline):
    project = create(client, auth_headers)
    updated = client.post(f"/projects/{project['id']}/documents", files=[("files", ("extra.md", b"# nota", "text/markdown"))],
                          headers=auth_headers).json()
    assert updated["latestAnalysisId"] != project["latestAnalysisId"]


def test_graph_trace_and_canonical(client, auth_headers, fake_pipeline):
    analysis_id = create(client, auth_headers)["latestAnalysisId"]
    graph = client.get(f"/analyses/{analysis_id}/graph", headers=auth_headers).json()
    kinds = {n["kind"] for n in graph["nodes"]}
    assert {"class", "criterion", "rule", "evidence", "source"} <= kinds
    assert graph["edges"]
    trace = client.get(f"/analyses/{analysis_id}/graph/trace/criterion:NOV", headers=auth_headers).json()
    assert any(n["nodeId"] == "source:PRJ90-S02" for n in trace)
    canonical = client.get(f"/analyses/{analysis_id}/canonical", headers=auth_headers).json()
    assert canonical["projectCode"] == "PRJ90"
    assert any(f["status"] == "pendente_validacao" for f in canonical["files"])


def test_analyses_of_other_users_are_hidden(client, auth_headers, fake_pipeline):
    analysis_id = create(client, auth_headers)["latestAnalysisId"]
    other = client.post("/auth/register", json={"email": "z@sts.com", "password": "zzzzzzzz"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/analyses/{analysis_id}/status", headers=headers).status_code == 404
    assert client.get("/analyses/bad-id/status", headers=headers).status_code == 404


@pytest.fixture
def package_dir(tmp_path, monkeypatch):
    for name in ("PRJ90", "PRJ91"):
        folder = tmp_path / "casos" / name
        for f in synthetic_package():
            target = folder / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.data.replace(b"PRJ90", name.encode()))
    monkeypatch.setattr(settings, "package_dir", tmp_path)
    return tmp_path


def test_batch_from_package_folder(client, auth_headers, fake_pipeline, package_dir):
    batch = client.post("/batches", json={"packageDir": str(package_dir / "casos")}, headers=auth_headers).json()
    assert batch["total"] == 2
    panel = client.get(f"/batches/{batch['id']}", headers=auth_headers).json()
    assert panel["counts"]["concluida"] == 2
    assert {item["code"] for item in panel["items"]} == {"PRJ90", "PRJ91"}
    by_code = {item["code"]: item for item in panel["items"]}
    assert by_code["PRJ90"]["suggestedClass"] == "eligible"
    assert by_code["PRJ91"]["suggestedClass"]  # fake evidence cites PRJ90 ids, so PRJ91 is downgraded by the gates
    assert client.get("/batches", headers=auth_headers).json()[0]["id"] == batch["id"]


def test_batch_rejects_paths_outside_package_dir(client, auth_headers, fake_pipeline, package_dir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("fora")
    response = client.post("/batches", json={"packageDir": str(outside)}, headers=auth_headers)
    assert response.status_code == 403


def test_batch_from_zip_with_several_projects(client, auth_headers, fake_pipeline):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in ("PRJ90", "PRJ91"):
            for f in synthetic_package():
                archive.writestr(f"lote/{name}/{f.path}", f.data)
    batch = client.post("/batches/upload", files=[("file", ("lote.zip", buffer.getvalue(), "application/zip"))],
                        headers=auth_headers).json()
    assert batch["total"] == 2
