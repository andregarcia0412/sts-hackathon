import os

# Must run before `backend` is imported: Settings is built at import time.
os.environ.update(
    MONGODB_DB="sts_test",
    JWT_ACCESS_SECRET="test-access-secret-at-least-32-bytes-long",
    JWT_REFRESH_SECRET="test-refresh-secret-at-least-32-bytes-long",
    ACCESS_TOKEN_EXPIRE_MINUTES="15",
    REFRESH_TOKEN_EXPIRE_DAYS="7",
    SEED_EMAIL_PATTERN="seed{n}@sts.com",
    SEED_PASSWORD="seed-password",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.main import app  # noqa: E402


def _drop_test_db() -> None:
    with MongoClient(settings.mongodb_uri) as mongo:
        mongo.drop_database(settings.mongodb_db)


@pytest.fixture
def client():
    _drop_test_db()
    with TestClient(app) as test_client:
        yield test_client
    _drop_test_db()


@pytest.fixture
def users_collection():
    with MongoClient(settings.mongodb_uri) as mongo:
        yield mongo[settings.mongodb_db]["users"]
