import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from ai_microservice.jobs import JobStore, get_job_store
from ai_microservice.main import app
from ai_microservice.modules.novelty.router import get_pipeline


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class FakePipeline:
    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.received = None

    async def run(self, job_id, dossie, entrevista, data_inicio):
        self.received = (dossie, entrevista, data_inicio)
        self.store.set_step(job_id, "extracao", "done")
        self.store.finish(job_id, {"criterio": "novidade"})


def make_client(monkeypatch) -> tuple[TestClient, FakePipeline]:
    store = JobStore()
    pipeline = FakePipeline(store)
    app.dependency_overrides = {get_job_store: lambda: store, get_pipeline: lambda: pipeline}
    monkeypatch.setattr("ai_microservice.modules.novelty.router.extract_text", lambda data: data.decode())
    return TestClient(app), pipeline


def test_post_returns_job_and_get_returns_result(monkeypatch):
    client, pipeline = make_client(monkeypatch)
    response = client.post(
        "/novelty/analyses",
        files={"dossie": ("d.pdf", b"texto dossie"), "entrevista": ("e.pdf", b"texto entrevista")},
        data={"data_inicio": "2025-01-06"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert pipeline.received[0] == "texto dossie" and pipeline.received[1] == "texto entrevista"
    assert str(pipeline.received[2]) == "2025-01-06"

    job = client.get(f"/novelty/analyses/{job_id}").json()
    assert job["status"] == "done"
    assert job["result"] == {"criterio": "novidade"}
    assert job["progress"]["extracao"] == "done" and job["progress"]["regras"] == "pending"
    app.dependency_overrides = {}


def test_interview_is_optional(monkeypatch):
    client, pipeline = make_client(monkeypatch)
    assert client.post("/novelty/analyses", files={"dossie": ("d.pdf", b"x")}).status_code == 202
    assert pipeline.received[1] is None
    app.dependency_overrides = {}


def test_pdf_without_text_is_rejected():
    store = JobStore()
    app.dependency_overrides = {get_job_store: lambda: store, get_pipeline: lambda: FakePipeline(store)}
    response = TestClient(app).post("/novelty/analyses", files={"dossie": ("d.pdf", blank_pdf())})
    assert response.status_code == 422
    assert "sem texto" in response.json()["detail"]
    app.dependency_overrides = {}


def test_unknown_job_is_404():
    assert TestClient(app).get("/novelty/analyses/nope").status_code == 404
