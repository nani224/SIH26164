from __future__ import annotations

import os
from collections.abc import Iterator

# Must be set before api.db is first imported (it reads DATABASE_URL at
# module load time) -- gives the whole test session one shared in-memory
# SQLite database (see api/db.py's StaticPool handling for "sqlite://").
os.environ.setdefault("DATABASE_URL", "sqlite://")
# Test-only: lets tests isolate rate-limit buckets per test via
# X-Test-Client-Id (see api/rate_limiter.py) -- never set in production.
os.environ.setdefault("ECDAT_RATE_LIMIT_TRUST_TEST_HEADER", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import db  # noqa: E402
from api.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    """Create tables + seed once per test session.

    Independent of the FastAPI lifespan (which also calls init_db() for
    real app startup) so tests that talk to api.store directly -- without
    going through a TestClient -- still get a ready database.
    """
    db.init_db()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
