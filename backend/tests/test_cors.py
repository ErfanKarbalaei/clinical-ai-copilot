"""CORS regression tests — browser preflight behavior for the frontend."""

from fastapi.testclient import TestClient

from app.main import app

PREFLIGHT_HEADERS = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def preflight(client: TestClient, origin: str):
    return client.options(
        "/api/v1/patients/1/chat",
        headers={"Origin": origin, **PREFLIGHT_HEADERS},
    )


def test_preflight_allowed_for_default_frontend_port(client: TestClient):
    response = preflight(client, "http://localhost:3000")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_preflight_allowed_for_alternate_frontend_port(client: TestClient):
    response = preflight(client, "http://localhost:3100")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3100"


def test_preflight_rejected_for_unknown_origin(client: TestClient):
    response = preflight(client, "http://evil.example")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_actual_request_carries_allow_origin(client: TestClient):
    response = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:3100"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3100"
