import pytest

from backend.review.reanalysis import ContestationVerdictOut
from tests.conftest import package_upload


@pytest.fixture
def project(client, auth_headers, fake_pipeline):
    return client.post("/projects", data={"name": "PRJ90 fila"}, files=package_upload(), headers=auth_headers).json()


def analyses(client, headers, project):
    return client.get(f"/projects/{project['id']}/analyses", headers=headers).json()


def test_analyses_in_frontend_shape(client, auth_headers, project):
    [analysis] = analyses(client, auth_headers, project)
    assert analysis["framework"] == "frascati"
    assert analysis["suggestedClass"] == "eligible"
    novelty = analysis["criteria"][0]
    assert novelty["id"] == "crit-novelty" and novelty["state"] == "DEMONSTRADA NO RECORTE"
    rule = next(r for r in novelty["rules"] if r["code"] == "NOV-D2")
    assert rule["evidences"][0]["projectExcerpt"]["excerpt"].startswith("Ambos falham")
    assert rule["scoreExplanation"]["factors"][0]["points"] == 100


def test_project_list_summary(client, auth_headers, project):
    item = client.get("/projects", headers=auth_headers).json()["items"][0]
    assert item["frameworks"] == ["frascati"]
    assert item["suggestedClass"] == "eligible"
    assert {s["criterionKey"] for s in item["scoreSummary"]} >= {"novelty", "reproducibility"}
    assert item["lastDecision"] is None


def test_decision_is_append_only_and_keeps_the_suggestion(client, auth_headers, project):
    analysis_id = project["latestAnalysisId"]
    body = {"projectId": project["id"], "analysisId": analysis_id, "outcome": "not_eligible",
            "justification": "Comparador não é independente.", "analystName": "Ana Analista",
            "ruleOverrides": [{"ruleId": "crit-novelty.rule-nov-d2", "note": "fonte fraca"}]}
    first = client.post(f"/projects/{project['id']}/decisions", json=body, headers=auth_headers)
    assert first.status_code == 201
    assert first.json()["suggestedClass"] == "eligible"
    client.post(f"/projects/{project['id']}/decisions", json=body | {"outcome": "eligible_with_caveats"}, headers=auth_headers)
    trail = client.get(f"/projects/{project['id']}/decisions", headers=auth_headers).json()
    assert [d["outcome"] for d in trail] == ["not_eligible", "eligible_with_caveats"]
    assert client.get(f"/projects/{project['id']}", headers=auth_headers).json()["status"] == "decided"
    graph = client.get(f"/analyses/{analysis_id}/graph", headers=auth_headers).json()
    assert sum(n["kind"] == "decision" for n in graph["nodes"]) == 2
    assert any(e["kind"] == "decidiu" and e["target"] == "class:suggested" for e in graph["edges"])
    assert analyses(client, auth_headers, project)[0]["suggestedClass"] == "eligible"  # suggestion untouched
    summary = client.get("/projects", headers=auth_headers).json()["items"][0]
    assert summary["lastDecision"]["outcome"] == "eligible_with_caveats"


def test_decision_requires_justification_and_valid_outcome(client, auth_headers, project):
    base = {"projectId": project["id"], "analysisId": project["latestAnalysisId"], "analystName": "Ana"}
    assert client.post(f"/projects/{project['id']}/decisions", json=base | {"outcome": "eligible", "justification": " "},
                       headers=auth_headers).status_code == 422
    assert client.post(f"/projects/{project['id']}/decisions", json=base | {"outcome": "maybe", "justification": "x"},
                       headers=auth_headers).status_code == 422


def contest(client, headers, project, node_id, reason="polarity", argument="O trecho do metodo.md §1 diz o contrário."):
    body = {"projectId": project["id"], "analysisId": project["latestAnalysisId"], "nodeId": node_id,
            "nodeLabel": "1.1 NOV-D2", "reason": reason, "argument": argument, "author": "Ana"}
    response = client.post(f"/projects/{project['id']}/contestations", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def evidence_node(client, headers, project, code="NOV-D2"):
    rule = next(r for c in analyses(client, headers, project)[0]["criteria"] for r in c["rules"] if r["code"] == code)
    return f"crit-{'novelty'}.{rule['id']}.{rule['evidences'][0]['id']}", rule


def test_accepted_polarity_contestation_changes_the_view_not_the_analysis(client, auth_headers, project, fake_pipeline):
    fake_pipeline.handlers[ContestationVerdictOut] = ContestationVerdictOut(verdict="accepted", explicacao="O trecho descreve limitação.")
    node_id, rule = evidence_node(client, auth_headers, project)
    contestation = contest(client, auth_headers, project, node_id)
    assert contestation["status"] == "open"
    resolved = client.post(f"/contestations/{contestation['id']}/reanalysis", headers=auth_headers).json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution"]["verdict"] == "accepted"
    fields = {c["field"] for c in resolved["resolution"]["changes"]}
    assert {"polarity", "score"} <= fields
    view = analyses(client, auth_headers, project)[0]
    new_rule = next(r for r in view["criteria"][0]["rules"] if r["code"] == "NOV-D2")
    assert new_rule["evidences"][0]["polarity"] == "negative"
    assert new_rule["score"] == 0
    assert view["adjustments"][0]["contestationId"] == contestation["id"]
    # resolving twice returns the same resolution
    again = client.post(f"/contestations/{contestation['id']}/reanalysis", headers=auth_headers).json()
    assert again["resolution"]["resolvedAt"] == resolved["resolution"]["resolvedAt"]


def test_maintained_contestation_changes_nothing(client, auth_headers, project, fake_pipeline):
    fake_pipeline.handlers[ContestationVerdictOut] = ContestationVerdictOut(verdict="maintained", explicacao="O trecho sustenta a regra.")
    node_id, _ = evidence_node(client, auth_headers, project)
    contestation = contest(client, auth_headers, project, node_id)
    resolved = client.post(f"/contestations/{contestation['id']}/reanalysis", headers=auth_headers).json()
    assert resolved["resolution"]["verdict"] == "maintained"
    assert resolved["resolution"]["changes"] == []
    assert analyses(client, auth_headers, project)[0]["adjustments"] == []


def test_rule_contestation_reruns_the_sub_agent_with_the_argument(client, auth_headers, project, fake_pipeline):
    from backend.criteria.doc_sub import DocSubOut

    def doc(messages):
        assert "<argumento_do_analista>" in messages[-1]["content"]
        return DocSubOut(evidencias=[{"regra_id": "NOV-D3", "fragmento_id": "PRJ90-EV06#2", "quote": "Ordenar lotes por grafo",
                                      "polaridade": "positiva", "justificativa": "o como técnico"}])

    fake_pipeline.handlers[DocSubOut] = doc
    contestation = contest(client, auth_headers, project, "crit-novelty.rule-nov-d3", reason="missing_evidence",
                           argument="O §2 descreve o mecanismo técnico.")
    resolved = client.post(f"/contestations/{contestation['id']}/reanalysis", headers=auth_headers).json()
    assert resolved["resolution"]["verdict"] == "accepted"
    rule = next(r for r in analyses(client, auth_headers, project)[0]["criteria"][0]["rules"] if r["code"] == "NOV-D3")
    assert rule["score"] == 100 and rule["evidences"][0]["adjusted"] is True


def test_unknown_node_is_rejected(client, auth_headers, project):
    contestation = contest(client, auth_headers, project, "crit-novelty.rule-xyz-1")
    assert client.post(f"/contestations/{contestation['id']}/reanalysis", headers=auth_headers).status_code == 422


def test_rule_decisions_and_evidence_reviews_are_append_only(client, auth_headers, project):
    base = {"projectId": project["id"], "analysisId": project["latestAnalysisId"], "nodeId": "crit-novelty.rule-nov-d2",
            "nodeLabel": "1.1 NOV-D2", "author": "Ana"}
    client.post(f"/projects/{project['id']}/rule-decisions", json=base | {"rating": "partial", "suggested": "sustained",
                                                                           "justification": "fonte única"}, headers=auth_headers)
    client.post(f"/projects/{project['id']}/rule-decisions", json=base | {"rating": "sustained", "justification": "ok"},
                headers=auth_headers)
    assert [d["rating"] for d in client.get(f"/projects/{project['id']}/rule-decisions", headers=auth_headers).json()] == [
        "partial", "sustained"]
    review = client.post(f"/projects/{project['id']}/evidence-reviews", json=base | {"verdict": "discarded", "note": "fora"},
                         headers=auth_headers)
    assert review.status_code == 201 and review.json()["id"]
    assert len(client.get(f"/projects/{project['id']}/evidence-reviews", headers=auth_headers).json()) == 1


def test_analyses_null_while_processing(client, auth_headers):
    from backend.analyses.jobs import JobRunner
    from backend.main import app

    app.state.runner = JobRunner(1)  # real background runner: request returns before the analysis ends
    project = client.post("/projects", data={"name": "x"}, files=[("files", ("a.md", b"# a", "text/markdown"))],
                          headers=auth_headers).json()
    assert client.get(f"/projects/{project['id']}/analyses", headers=auth_headers).json() in (None, [])
