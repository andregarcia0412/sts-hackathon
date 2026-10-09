def test_rules_require_auth(client):
    assert client.get("/regras").status_code == 401


def test_list_rules_loaded_on_startup(client, auth_headers):
    rules = client.get("/regras", headers=auth_headers).json()
    assert len(rules) == 90
    nov_web = client.get("/regras", params={"criterio": "NOV", "bloco": "web"}, headers=auth_headers).json()
    assert [r["id"] for r in nov_web] == [f"NOV-W{n}" for n in range(1, 9)]


def test_get_rule_by_id(client, auth_headers):
    rule = client.get("/regras/cri-w2", headers=auth_headers).json()
    assert rule["id"] == "CRI-W2"
    assert rule["roteamento"] == ["configuracao_documentada"]
    assert client.get("/regras/XYZ-1", headers=auth_headers).status_code == 404


def test_cors_allows_frontend_origin(client):
    response = client.options(
        "/regras", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
