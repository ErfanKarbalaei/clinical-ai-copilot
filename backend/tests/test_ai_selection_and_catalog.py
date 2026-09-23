"""Runtime provider/model selection + catalog tests (all HTTP mocked).

Covers the Gemini + OpenRouter architecture:
- build_provider() validation (registry ids, model is never a URL)
- GET /ai/providers catalog (configured providers, omissions, auth)
- runtime selection through the persistent chat (gemini / openrouter /
  invalid → 422 / no selection → env defaults)
"""

import json

import httpx
import pytest

from app.core.config import get_settings
from app.services import ai, ai_catalog
from app.services.ai import (
    AIInvalidSelectionError,
    PROVIDER_IDS,
    build_provider,
)

REQUESTS: list[httpx.Request] = []


def _mock_http(monkeypatch, handler):
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original_client(transport=transport, timeout=kwargs.get("timeout"))
    )


def _ok(request: httpx.Request) -> httpx.Response:
    REQUESTS.append(request)
    return httpx.Response(200, json={"choices": [{"message": {"content": "پاسخ"}}]})


@pytest.fixture(autouse=True)
def _capture():
    REQUESTS.clear()


@pytest.fixture()
def catalog_env(monkeypatch):
    """OpenRouter configured (key + catalog reachable via mocks)."""
    monkeypatch.setattr(get_settings(), "OPENROUTER_API_KEY", "or-key-test")
    ai_catalog.invalidate_cache()
    yield
    ai_catalog.invalidate_cache()


# --- provider construction / validation ---


def test_unknown_provider_rejected():
    with pytest.raises(AIInvalidSelectionError, match="unknown provider"):
        build_provider("evil-gateway", "m")


def test_model_from_frontend_never_a_url():
    with pytest.raises(AIInvalidSelectionError):
        build_provider("openrouter", "https://evil.example.com")  # too long → invalid


def test_model_rejects_embedded_url_and_spaces(catalog_env):
    with pytest.raises(AIInvalidSelectionError, match="plain model id"):
        build_provider("openrouter", "http://x/y model")
    with pytest.raises(AIInvalidSelectionError, match="plain model id"):
        build_provider("openrouter", "some model")


def test_registry_ids():
    assert set(PROVIDER_IDS) == {"gemini", "openrouter", "openai_compatible"}


# --- catalog (GET /ai/providers) ---


def _auth_headers(db_session):
    from app.core.security import create_access_token
    from app.models import User

    user = User(
        email="cat-user@testcompany.com",
        password_hash="x",
        full_name="کاتالوگ",
    )
    db_session.add(user)
    db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def test_catalog_includes_gemini_and_openrouter(api_client, db_session, catalog_env, monkeypatch):
    monkeypatch.setattr(get_settings(), "AI_API_KEY", "g-key")

    def models_handler(request: httpx.Request) -> httpx.Response:
        REQUESTS.append(request)
        return httpx.Response(200, json={"data": [{"id": "anthropic/claude-sonnet-5", "name": "Claude Sonnet 5"}]})

    _mock_http(monkeypatch, models_handler)
    response = api_client.get("/api/v1/ai/providers", headers=_auth_headers(db_session))

    assert response.status_code == 200
    catalog = {p["id"]: p for p in response.json()["providers"]}
    assert "gemini" in catalog and catalog["gemini"]["models"][0]["id"] == "gemini-3.6-flash"
    assert catalog["openrouter"]["models"] == [
        {"id": "anthropic/claude-sonnet-5", "name": "Claude Sonnet 5"}
    ]
    # openrouter discovery hits the public /models endpoint
    or_request = [r for r in REQUESTS if "openrouter.ai" in str(r.url)][0]
    assert or_request.url.path.endswith("/models")
    # no secrets anywhere in the response
    assert "or-key-test" not in response.text and "g-key" not in response.text


def test_catalog_omits_unconfigured_gemini(api_client, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "AI_API_KEY", "")
    monkeypatch.setattr(get_settings(), "OPENROUTER_API_KEY", "")
    ai_catalog.invalidate_cache()

    def handler(request):
        return httpx.Response(200, json={"data": [{"id": "openrouter/x", "name": "X"}]})

    _mock_http(monkeypatch, handler)
    response = api_client.get("/api/v1/ai/providers", headers=_auth_headers(db_session))
    ids = [p["id"] for p in response.json()["providers"]]
    assert "gemini" not in ids  # no key → omitted
    assert "openrouter" in ids  # public catalog works keyless


def test_catalog_discovery_failure_omits_not_fabricates(api_client, db_session, catalog_env, monkeypatch):
    def handler(request):
        return httpx.Response(500, json={"error": "down"})

    _mock_http(monkeypatch, handler)
    response = api_client.get("/api/v1/ai/providers", headers=_auth_headers(db_session))
    ids = [p["id"] for p in response.json()["providers"]]
    assert "openrouter" not in ids  # failed → omitted, no fake models
    assert response.status_code == 200  # rest of catalog stays usable


def test_catalog_requires_auth(db_session):
    """Anonymous → 401 (REAL auth dependency, like every other endpoint)."""
    from fastapi.testclient import TestClient
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        assert client.get("/api/v1/ai/providers").status_code == 401
    finally:
        app.dependency_overrides.clear()


# --- runtime selection through the persistent chat ---


def _fake_openai_style(monkeypatch):
    """Make any OpenAI-style provider return a captured, canned answer."""
    original = httpx.Client

    def handler(request):
        REQUESTS.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=transport, timeout=kw.get("timeout")))


def _patient_and_conversation(api_client, db_session):
    from app.core.security import create_access_token, hash_password
    from app.models import Patient, PatientUserAccess, User

    user = User(
        email="sel-doc@testcompany.com", password_hash=hash_password("p-pass-123"),
        full_name="پزشک انتخاب", role="doctor",
    )
    db_session.add(user)
    db_session.flush()
    patient = Patient(first_name="ب", last_name="م")
    db_session.add(patient)
    db_session.flush()
    db_session.add(PatientUserAccess(patient_id=patient.id, user_id=user.id))
    db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user)}"}
    conv = api_client.post(
        f"/api/v1/patients/{patient.id}/conversations", json={}, headers=headers
    ).json()
    return headers, conv


def test_chat_selection_openrouter_hits_openrouter(api_client, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "OPENROUTER_API_KEY", "or-key")
    headers, conv = _patient_and_conversation(api_client, db_session)
    _fake_openai_style(monkeypatch)

    response = api_client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "سلام", "provider": "openrouter", "model": "anthropic/claude-sonnet-5"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    sent = [r for r in REQUESTS if "openrouter.ai" in str(r.url)][-1]
    assert "openrouter.ai/api/v1/chat/completions" in str(sent.url)
    assert json.loads(sent.content)["model"] == "anthropic/claude-sonnet-5"


def test_chat_selection_gemini_hits_gemini(api_client, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "AI_API_KEY", "g-key")
    monkeypatch.setattr(get_settings(), "AI_PROVIDER", "openai_compatible")
    monkeypatch.setattr(get_settings(), "AI_BASE_URL", "http://default.example/v1")
    headers, conv = _patient_and_conversation(api_client, db_session)

    original = httpx.Client
    REQUESTS.clear()

    def handler(request):
        REQUESTS.append(request)
        body = {"candidates": [{"content": {"parts": [{"text": "جواب"}]}}]}
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=transport, timeout=kw.get("timeout")))

    response = api_client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "سلام", "provider": "gemini", "model": "gemini-2.5-flash"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    sent = REQUESTS[-1]
    assert "generativelanguage.googleapis.com" in str(sent.url)
    assert "gemini-2.5-flash" in str(sent.url)


def test_chat_selection_invalid_provider_422(api_client, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "AI_API_KEY", "g-key")
    headers, conv = _patient_and_conversation(api_client, db_session)
    response = api_client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "سلام", "provider": "not-a-provider"},
        headers=headers,
    )
    assert response.status_code == 422


def test_chat_without_selection_uses_env_default(api_client, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(get_settings(), "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(get_settings(), "AI_MODEL", "x/y:free")
    headers, conv = _patient_and_conversation(api_client, db_session)
    _fake_openai_style(monkeypatch)

    response = api_client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "سلام"},  # no provider/model → env defaults
        headers=headers,
    )
    assert response.status_code == 200
    sent = [r for r in REQUESTS if "openrouter.ai" in str(r.url)][-1]
    assert json.loads(sent.content)["model"] == "x/y:free"
