"""Shared fixtures for integration tests.

Integration tests exercise the real FastAPI app wired to a real PostgreSQL
database and a real Redis instance (connection info from the environment,
defaulting to the values in .env.example). Each test gets a clean `documents`
table and a flushed Redis DB so tests are independent and order-proof.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://searchsphere:searchsphere@localhost:5432/searchsphere"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/3")

from app.config import get_settings  # noqa: E402
from app.services.index_manager import get_index_manager  # noqa: E402
from app.storage.cache import get_redis_client  # noqa: E402
from app.storage.db import Base, SessionLocal, engine  # noqa: E402
from app.storage import models  # noqa: E402,F401  (import registers Document on Base.metadata)


@pytest.fixture(autouse=True)
def clean_state():
    """Runs around every test: empty tables, flush cache, reset the index."""
    get_settings.cache_clear()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE documents RESTART IDENTITY")

    redis_client = get_redis_client()
    redis_client.flushdb()

    get_index_manager.cache_clear()

    yield

    redis_client.flushdb()


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
