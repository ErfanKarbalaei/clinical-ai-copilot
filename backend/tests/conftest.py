"""Shared pytest fixtures.

- ``client``: HTTP test client for the FastAPI application (no DB needed).
- ``db_engine`` / ``db_session``: a real PostgreSQL test database
  (``<POSTGRES_DB>_test``). Tests that need the database are skipped
  automatically when PostgreSQL is not reachable, so the suite stays green
  without infrastructure (e.g. on CI or offline machines).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

TEST_DATABASE_NAME = f"{settings.POSTGRES_DB}_test"
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/" + TEST_DATABASE_NAME


@pytest.fixture()
def client() -> TestClient:
    """HTTP test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture()
def api_client(db_session) -> TestClient:
    """HTTP test client whose DB dependency uses the isolated test session."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _create_test_database_if_missing() -> None:
    """Create the test database via the server's maintenance database."""
    admin_url = settings.database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DATABASE_NAME},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def db_engine():
    """Engine for the PostgreSQL test database (fresh schema per session)."""
    try:
        _create_test_database_if_missing()
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(engine)
    except OperationalError as error:
        pytest.skip(
            f"PostgreSQL is not reachable ({error}). "
            "Start it with: docker compose up -d postgres"
        )
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """A transactional session per test — rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()
