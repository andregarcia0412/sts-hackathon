"""Testes da integração frontend ↔ ai-microservice: /ai-projects + CORS."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent


def _client() -> TestClient:
    from ai_microservice.main import app

    return TestClient(app)


def test_root_ok():
    c = _client()
    r = c.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ai_projects_lista_prj01_com_versao():
    """/ai-projects lista os grafos salvos — o repodata tem PRJ01/v1."""
    c = _client()
    r = c.get("/ai-projects")
    assert r.status_code == 200
    projects = r.json()["projects"]
    prj01 = [p for p in projects if p["project_id"] == "PRJ01"]
    assert prj01, "PRJ01 com grafo salvo deve constar"
    assert prj01[0]["version"].startswith("v")
    assert isinstance(prj01[0].get("nodes"), int)


def test_cors_preflight_do_frontend():
    """O preflight do Vite dev origin passa (allow_methods GET/POST)."""
    c = _client()
    r = c.options(
        "/ai-projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-methods"] in ("GET, POST", "GET,POST")


def test_cors_origem_desconhecida_nao_tem_header():
    c = _client()
    r = c.get("/ai-projects", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_graph_endpoint_devolve_nodes_para_o_frontend():
    """GET /graph/PRJ01 (usado pelo adapter do front) traz nodes/edges/version."""
    c = _client()
    r = c.get("/graph/PRJ01")
    assert r.status_code == 200
    body = r.json()
    assert body["version"].startswith("v")
    assert len(body["nodes"]) > 0 and len(body["edges"]) > 0
    ids = {n["id"] for n in body["nodes"]}
    assert "criterio:novidade" in ids