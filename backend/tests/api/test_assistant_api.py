from backend.assistant.answer import AnswerOut
from backend.assistant.norms import chunk_pages, norm_index
from backend.main import app
from tests.conftest import package_upload


def setup_project(client, headers, fake_pipeline):
    app.state.norm_index = norm_index(chunk_pages("Lei 11.196", ["Art. 17. A pessoa jurídica poderá usufruir de incentivos."]))
    project = client.post("/projects", data={"name": "PRJ90"}, files=package_upload(), headers=headers).json()
    return project, client.get(f"/projects/{project['id']}/analyses", headers=headers).json()[0]


def test_ask_about_the_analysis(client, auth_headers, fake_pipeline):
    _, analysis = setup_project(client, auth_headers, fake_pipeline)
    fake_pipeline.handlers[AnswerOut] = AnswerOut(paragrafos=["Os cinco critérios estão na coluna P&D."], fontes=["crit-novelty"])
    answer = client.post("/assistant/ask", headers=auth_headers, json={
        "question": "por que é elegível?",
        "context": {"screen": "analysis", "analysis": analysis, "selectedNodeId": None}}).json()
    assert answer["blocks"][0] == {"type": "text", "text": "Os cinco critérios estão na coluna P&D."}
    assert answer["sources"] == [{"nodeId": "crit-novelty", "label": "Novidade"}]


def test_ask_about_the_norm_without_analysis(client, auth_headers, fake_pipeline):
    setup_project(client, auth_headers, fake_pipeline)
    chunk_id = app.state.norm_index.chunks[0].id
    fake_pipeline.handlers[AnswerOut] = AnswerOut(paragrafos=["O art. 17 trata dos incentivos."], fontes=[f"norma:{chunk_id}"])
    answer = client.post("/assistant/ask", headers=auth_headers, json={"question": "o que diz a lei sobre incentivos?",
                                                                        "context": {"screen": "analysis"}}).json()
    assert answer["sources"][0]["label"] == "Lei 11.196 — Art. 17 (p. 1)"


def test_debate_opening_and_reply(client, auth_headers, fake_pipeline):
    _, analysis = setup_project(client, auth_headers, fake_pipeline)
    opening = client.post("/assistant/debate", headers=auth_headers, json={
        "nodeId": "crit-novelty", "context": {"screen": "analysis", "analysis": analysis}}).json()
    assert opening["actions"][0]["type"] == "record-contestation"
    fake_pipeline.handlers[AnswerOut] = AnswerOut(paragrafos=["Mantenho a leitura."], fontes=["crit-novelty"])
    reply = client.post("/assistant/ask", headers=auth_headers, json={
        "question": "por que não é indeterminada?",
        "context": {"screen": "analysis", "analysis": analysis, "debateNodeId": "crit-novelty"}}).json()
    assert reply["actions"][0]["nodeId"] == "crit-novelty"


def test_other_users_analysis_is_not_readable(client, auth_headers, fake_pipeline):
    _, analysis = setup_project(client, auth_headers, fake_pipeline)
    other = client.post("/auth/register", json={"email": "o@sts.com", "password": "oooooooo"}).json()
    response = client.post("/assistant/ask", headers={"Authorization": f"Bearer {other['access_token']}"},
                           json={"question": "x", "context": {"screen": "analysis", "analysis": {"id": analysis["id"]}}})
    assert response.status_code == 404
