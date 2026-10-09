import csv
import io

from pypdf import PdfReader

from tests.conftest import package_upload


def project(client, headers):
    return client.post("/projects", data={"name": "PRJ90 fila"}, files=package_upload(), headers=headers).json()


def test_report_json_csv_pdf(client, auth_headers, fake_pipeline):
    created = project(client, auth_headers)
    analysis_id = created["latestAnalysisId"]
    client.post(f"/projects/{created['id']}/decisions", headers=auth_headers, json={
        "projectId": created["id"], "analysisId": analysis_id, "outcome": "eligible",
        "justification": "Concordo com a sugestão.", "analystName": "Ana Analista"})

    report = client.get(f"/analyses/{analysis_id}/report.json", headers=auth_headers).json()
    assert report["classificacao"] == "Elegível"
    assert report["decisoesAnalista"][0]["analystName"] == "Ana Analista"

    response = client.get(f"/analyses/{analysis_id}/report.csv", headers=auth_headers)
    assert response.headers["content-type"].startswith("text/csv")
    assert "PRJ90" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[0]["projeto_id"] == "PRJ90" and rows[0]["estado_2"] == "DEMONSTRADA NO RECORTE"

    pdf = client.get(f"/analyses/{analysis_id}/report.pdf", headers=auth_headers)
    assert pdf.headers["content-type"] == "application/pdf"
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Ana Analista" in text and "Concordo com a sugestão." in text


def test_report_needs_finished_analysis(client, auth_headers, fake_pipeline):
    from backend.analyses.jobs import JobRunner
    from backend.main import app

    app.state.runner = JobRunner(1)
    created = client.post("/projects", data={"name": "x"}, files=[("files", ("a.md", b"# a", "text/markdown"))],
                          headers=auth_headers).json()
    response = client.get(f"/analyses/{created['latestAnalysisId']}/report.json", headers=auth_headers)
    assert response.status_code in (404, 409)


def test_batch_report_csv(client, auth_headers, fake_pipeline, tmp_path, monkeypatch):
    from backend.config import settings
    from tests.factories import synthetic_package

    for f in synthetic_package():
        target = tmp_path / "PRJ90" / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.data)
    monkeypatch.setattr(settings, "package_dir", tmp_path)
    batch = client.post("/batches", json={"packageDir": str(tmp_path)}, headers=auth_headers).json()
    content = client.get(f"/batches/{batch['id']}/report.csv", headers=auth_headers).content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(content), delimiter=";"))
    assert [r["projeto_id"] for r in rows] == ["PRJ90"]
    assert len(rows[0]) == 27
