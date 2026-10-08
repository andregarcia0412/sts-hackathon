import io
import zipfile


def upload(client, headers, files, name="Projeto X", **form):
    return client.post(
        "/projects",
        data={"name": name, **form},
        files=[("files", (fname, content, "application/octet-stream")) for fname, content in files],
        headers=headers,
    )


def test_create_project_with_files(client, auth_headers):
    response = upload(client, auth_headers, [("metodo.md", b"# m"), ("dossie.pdf", b"%PDF-1")], company="ACME", freeText="desc")
    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "Projeto X"
    assert project["company"] == "ACME"
    assert project["freeText"] == "desc"
    assert project["status"] in {"processing", "ready", "error"}
    assert {d["fileName"] for d in project["documents"]} == {"metodo.md", "dossie.pdf"}
    doc = project["documents"][0]
    assert {"id", "fileName", "mimeType", "sizeBytes", "uploadedAt", "sha256"} <= set(doc)


def test_zip_upload_expands_files(client, auth_headers):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("PRJ90/evidencias/metodo.md", "# m")
        archive.writestr("PRJ90/dossie_projeto.pdf", "%PDF")
    project = upload(client, auth_headers, [("pacote.zip", buffer.getvalue())]).json()
    assert {d["fileName"] for d in project["documents"]} == {"evidencias/metodo.md", "dossie_projeto.pdf"}
    assert project["code"] == "PRJ90"


def test_project_needs_at_least_one_file(client, auth_headers):
    assert upload(client, auth_headers, []).status_code == 422


def test_get_and_list_only_own_projects(client, auth_headers):
    project = upload(client, auth_headers, [("a.md", b"1")]).json()
    assert client.get(f"/projects/{project['id']}", headers=auth_headers).json()["id"] == project["id"]

    other = client.post("/auth/register", json={"email": "other@sts.com", "password": "other-pass"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/projects/{project['id']}", headers=other_headers).status_code == 404
    page = client.get("/projects", headers=other_headers).json()
    assert page["total"] == 0 and page["items"] == []

    mine = client.get("/projects", headers=auth_headers).json()
    assert mine["total"] == 1
    assert mine["items"][0]["ownerId"] == project["ownerId"]


def test_unknown_project_is_404(client, auth_headers):
    assert client.get("/projects/000000000000000000000000", headers=auth_headers).status_code == 404
    assert client.get("/projects/not-an-id", headers=auth_headers).status_code == 404


def test_adding_a_document_with_same_name_supersedes_never_deletes(client, auth_headers):
    project = upload(client, auth_headers, [("metodo.md", b"v1")]).json()
    response = client.post(
        f"/projects/{project['id']}/documents",
        files=[("files", ("metodo.md", b"v2", "text/markdown"))],
        headers=auth_headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert [d["fileName"] for d in updated["documents"]] == ["metodo.md"]
    assert updated["documents"][0]["sizeBytes"] == 2
    assert len(updated["supersededDocuments"]) == 1


def test_projects_require_auth(client):
    assert client.get("/projects").status_code == 401
