from backend.config import settings
from backend.users.seed import SEED_USER_COUNT, seed_users


def seed_emails():
    return [settings.seed_email_pattern.format(n=n) for n in range(1, SEED_USER_COUNT + 1)]


def test_startup_seeds_users_that_can_log_in(client, users_collection):
    stored = sorted(doc["email"] for doc in users_collection.find())
    assert stored == sorted(seed_emails())

    for email in seed_emails():
        response = client.post(
            "/auth/login", json={"email": email, "password": settings.seed_password}
        )
        assert response.status_code == 200


def test_seed_is_idempotent(client, users_collection):
    client.portal.call(seed_users)
    assert users_collection.count_documents({}) == SEED_USER_COUNT
