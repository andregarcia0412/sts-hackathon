from datetime import UTC, datetime, timedelta

import jwt

from backend.auth.security import ALGORITHM
from backend.config import settings

EMAIL = "Alice@Example.com"
PASSWORD = "correct-horse"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_tokens_that_authenticate(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"

    me = client.get("/users/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"
    assert set(me.json()) == {"id", "email", "name"}
    assert me.json()["name"] == "alice"


def test_register_stores_lowercased_email_and_hash(client, users_collection):
    register(client)
    doc = users_collection.find_one({"email": "alice@example.com"})
    assert doc is not None
    assert set(doc) == {"_id", "email", "name", "password_hash"}
    assert doc["password_hash"].startswith("$argon2id$")
    assert PASSWORD not in doc["password_hash"]


def test_register_duplicate_email_is_conflict(client):
    register(client)
    response = register(client, email="ALICE@example.com")
    assert response.status_code == 409


def test_register_validates_input(client):
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login(client):
    register(client)
    ok = client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert {"access_token", "refresh_token"} <= set(ok.json())

    wrong = client.post("/auth/login", json={"email": EMAIL, "password": "wrong-password"})
    unknown = client.post("/auth/login", json={"email": "bob@example.com", "password": PASSWORD})
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_refresh_returns_new_working_pair(client):
    tokens = register(client).json()
    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert client.get("/users/me", headers=bearer(new_tokens["access_token"])).status_code == 200


def test_token_types_are_not_interchangeable(client):
    tokens = register(client).json()
    as_refresh = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    as_access = client.get("/users/me", headers=bearer(tokens["refresh_token"]))
    assert as_refresh.status_code == 401
    assert as_access.status_code == 401


def test_expired_access_token_is_rejected(client):
    user_id = client.get(
        "/users/me", headers=bearer(register(client).json()["access_token"])
    ).json()["id"]
    past = datetime.now(UTC) - timedelta(minutes=1)
    expired = jwt.encode(
        {"sub": user_id, "type": "access", "iat": past, "exp": past},
        settings.jwt_access_secret,
        algorithm=ALGORITHM,
    )
    assert client.get("/users/me", headers=bearer(expired)).status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers=bearer("garbage")).status_code == 401


def test_refresh_rejects_garbage(client):
    response = client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert response.status_code == 401


def test_register_accepts_display_name(client):
    tokens = client.post(
        "/auth/register", json={"email": "bob@example.com", "password": PASSWORD, "name": "Bob Analista"}
    ).json()
    assert client.get("/users/me", headers=bearer(tokens["access_token"])).json()["name"] == "Bob Analista"
