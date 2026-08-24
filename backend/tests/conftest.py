"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """HTTP test client for the FastAPI application."""
    return TestClient(app)
