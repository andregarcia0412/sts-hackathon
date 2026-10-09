import pytest

from backend.config import settings
from backend.report.builder import ANSWER_KEY_COLUMNS
from tests.factories import ELIGIBLE_STATES, synthetic_package

NAMES = {"NOV": "Novidade", "CRI": "Criatividade técnica", "INC": "Incerteza tecnológica", "SIS": "Sistematicidade",
         "REP": "Transferência/reprodução"}


def _write_project(folder, code):
    for f in synthetic_package():
        target = folder / code / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.data.replace(b"PRJ90", code.encode()))


@pytest.fixture
def package_root(tmp_path, monkeypatch):
    """The challenge layout: two historical projects with answer key, one case with a preliminary reading."""
    _write_project(tmp_path / "01_projetos" / "01_historico", "PRJ90")
    _write_project(tmp_path / "01_projetos" / "01_historico", "PRJ92")
    _write_project(tmp_path / "01_projetos" / "02_casos_para_analise", "PRJ91")
    rows = []
    for code, label in (("PRJ90", "Elegível"), ("PRJ92", "Não elegível")):
        row = {"projeto_id": code, "classificacao": label}
        for n, criterion in enumerate(NAMES, start=1):
            row |= {f"criterio_{n}": NAMES[criterion], f"estado_{n}": ELIGIBLE_STATES[criterion]}
        rows.append(";".join(row.get(c, "") for c in ANSWER_KEY_COLUMNS))
    (tmp_path / "historicos_classificados.csv").write_text(
        "﻿" + "\n".join([";".join(ANSWER_KEY_COLUMNS), *rows]), encoding="utf-8")
    (tmp_path / "leitura_preliminar.csv").write_text(
        "projeto_id;classificacao;divergencia_entrevista;divergencia_registro;fonte_que_prevalece\n"
        "PRJ91;Com ressalvas;400;412;PRJ91-S01\n", encoding="utf-8")
    monkeypatch.setattr(settings, "package_dir", tmp_path)
    return tmp_path


def test_benchmark_runs_both_sets_and_measures_against_each_reference(client, auth_headers, fake_pipeline, package_root):
    created = client.post("/benchmarks", json={"name": "smoke"}, headers=auth_headers)
    assert created.status_code == 202
    body = created.json()
    assert body["status"] == "concluido" and body["total"] == 3
    assert body["progress"]["concluida"] == 3
    assert body["config"]["answerKeySha256"] and body["config"]["models"]["doc"] == "fake-doc"

    metrics = client.get(f"/benchmarks/{body['id']}", headers=auth_headers).json()["metrics"]
    official, preliminary = metrics["accuracy"]["oficial"], metrics["accuracy"]["preliminar"]
    assert (official["n"], official["classHits"], official["classAccuracy"]) == (2, 1, 0.5)
    # the fake answers only fit PRJ90's fragment ids, so PRJ92 ends without numeric record → insufficient
    assert official["confusion"]["Não elegível"] == {"Evidência insuficiente": 1}
    assert official["misses"] == ["PRJ92: Não elegível → Evidência insuficiente"]
    assert official["stateAccuracy"]["NOV"] == 0.5
    assert preliminary["n"] == 1 and preliminary["classAccuracy"] == 0.0
    assert preliminary["plantedDivergences"] == 1
    assert metrics["reliability"]["failureRate"] == 0
    assert metrics["usage"]["total"]["calls"] > 0 and metrics["usage"]["tokensPerRun"]["mean"] > 0
    assert metrics["timing"]["totalS"]["n"] == 3 and set(metrics["bySet"]) == {"historico", "analise"}
    assert metrics["evidence"]["ruleCoverage"] > 0
    assert metrics["determinism"] is None


def test_benchmark_project_rows_and_csv(client, auth_headers, fake_pipeline, package_root):
    benchmark_id = client.post("/benchmarks", json={"projects": ["prj90"]}, headers=auth_headers).json()["id"]
    [row] = client.get(f"/benchmarks/{benchmark_id}/projects", headers=auth_headers).json()
    assert (row["code"], row["reference"], row["classHit"], row["stateHits"]) == ("PRJ90", "oficial", True, 5)
    assert row["tokens"] > 0
    csv = client.get(f"/benchmarks/{benchmark_id}/report.csv", headers=auth_headers)
    assert csv.headers["content-type"].startswith("text/csv")
    assert "PRJ90;" in csv.text and "classe_sugerida" in csv.text


def test_repeats_measure_determinism_and_benchmark_projects_stay_hidden(client, auth_headers, fake_pipeline, package_root):
    body = client.post("/benchmarks", json={"sets": ["historico"], "projects": ["PRJ90"], "repeats": 2},
                       headers=auth_headers).json()
    assert body["total"] == 2
    determinism = body["metrics"]["determinism"]
    assert determinism["classAgreement"] == 1.0 and determinism["evidenceJaccard"] == 1.0
    assert client.get("/projects", headers=auth_headers).json()["total"] == 0
    assert client.get("/batches", headers=auth_headers).json() == []
    assert client.get("/benchmarks", headers=auth_headers).json()[0]["headline"]["oficial.classAccuracy"] == 1.0


def test_compare_two_benchmarks(client, auth_headers, fake_pipeline, package_root):
    first = client.post("/benchmarks", json={"projects": ["PRJ90"]}, headers=auth_headers).json()["id"]
    second = client.post("/benchmarks", json={"projects": ["PRJ90", "PRJ92"]}, headers=auth_headers).json()["id"]
    comparison = client.get(f"/benchmarks/compare?base={first}&target={second}", headers=auth_headers).json()
    assert comparison["deltas"]["oficial.classAccuracy"] == {"base": 1.0, "target": 0.5, "delta": -0.5}
    assert comparison["modelsChanged"] == {} and comparison["catalogChanged"] is False


def test_benchmark_paths_must_stay_inside_package_dir(client, auth_headers, fake_pipeline, package_root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("fora")
    assert client.post("/benchmarks", json={"historicoDir": str(outside)}, headers=auth_headers).status_code == 403
    assert client.post("/benchmarks", json={"answerKey": "nao_existe.csv"}, headers=auth_headers).status_code == 404
    assert client.post("/benchmarks", json={"projects": ["PRJ99"]}, headers=auth_headers).status_code == 422


def test_benchmarks_are_scoped_to_their_owner(client, auth_headers, fake_pipeline, package_root):
    benchmark_id = client.post("/benchmarks", json={"projects": ["PRJ90"]}, headers=auth_headers).json()["id"]
    other = client.post("/auth/register", json={"email": "z@sts.com", "password": "zzzzzzzz"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/benchmarks/{benchmark_id}", headers=headers).status_code == 404
    assert client.get("/benchmarks/bad-id", headers=headers).status_code == 404


def test_rejudge_endpoint_creates_a_comparable_benchmark(client, auth_headers, fake_pipeline, package_root):
    source = client.post("/benchmarks", json={"projects": ["PRJ90"]}, headers=auth_headers).json()["id"]
    created = client.post(f"/benchmarks/{source}/rejudge", json={}, headers=auth_headers)
    assert created.status_code == 202
    body = client.get(f"/benchmarks/{created.json()['id']}", headers=auth_headers).json()
    assert body["status"] == "concluido" and body["config"]["rejudgedFrom"] == source
    assert body["progress"]["concluida"] == 1
    comparison = client.get(f"/benchmarks/compare?base={source}&target={body['id']}", headers=auth_headers).json()
    assert comparison["deltas"]["oficial.classAccuracy"]["delta"] == 0

    other = client.post("/auth/register", json={"email": "y@sts.com", "password": "yyyyyyyy"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post(f"/benchmarks/{source}/rejudge", json={}, headers=headers).status_code == 404


def test_close_a_benchmark_stuck_running(client, auth_headers, fake_pipeline, package_root):
    import asyncio

    from backend.analyses.models import Analysis

    body = client.post("/benchmarks", json={"projects": ["PRJ90", "PRJ92"]}, headers=auth_headers).json()

    async def reopen():  # as if the CLI had died with one analysis still running
        from beanie import PydanticObjectId

        from backend.benchmark.models import Benchmark

        benchmark = await Benchmark.get(PydanticObjectId(body["id"]))
        analysis = await Analysis.get(PydanticObjectId(benchmark.runs[1].analysis_id))
        analysis.status = "rodando"
        await analysis.save()
        benchmark.status, benchmark.metrics, benchmark.snapshots = "rodando", None, []
        await benchmark.save()

    client.portal.call(reopen) if hasattr(client, "portal") else asyncio.run(reopen())
    assert client.get(f"/benchmarks/{body['id']}", headers=auth_headers).json()["status"] == "rodando"
    closed = client.post(f"/benchmarks/{body['id']}/close", headers=auth_headers).json()
    assert closed["status"] == "concluido" and "fechado à força" in closed["errors"]
    assert closed["metrics"]["reliability"]["failed"] == 1


def test_report_html_endpoint(client, auth_headers, fake_pipeline, package_root):
    benchmark_id = client.post("/benchmarks", json={"projects": ["PRJ90"]}, headers=auth_headers).json()["id"]
    page = client.get(f"/benchmarks/{benchmark_id}/report.html", headers=auth_headers)
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert "Matriz de confusão" in page.text and "O que o sistema barrou" in page.text


def test_delivery_zip_endpoint(client, auth_headers, fake_pipeline, package_root):
    import io
    import zipfile

    benchmark_id = client.post("/benchmarks", json={"sets": ["analise"]}, headers=auth_headers).json()["id"]
    response = client.post(f"/benchmarks/{benchmark_id}/delivery", headers=auth_headers)
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "manifest.json" in names and "PRJ91/parecer.pdf" in names and "frontend/api_mock.json" in names
