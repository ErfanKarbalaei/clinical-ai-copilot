"""Clinical AI assistant tests (provider mocked — no real LLM calls)."""

import json

import httpx
import pytest

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.api.v1.routes.chat import (
    AI_NOT_CONFIGURED_DETAIL,
    AI_PROVIDER_ERROR_DETAIL,
)
from app.core.config import get_settings
from app.services import ai
from app.services.ai import (
    AIError,
    AIUnavailableError,
    GeminiProvider,
    OpenAICompatibleProvider,
)

PATIENTS_URL = "/api/v1/patients"
CHAT_URL = "/api/v1/patients/{patient_id}/chat"

CAPTURED: dict = {}


class FakeProvider:
    """Records the prompt and returns a canned answer."""

    def complete(self, *, system, user, history=None):
        CAPTURED["system"] = system
        CAPTURED["user"] = user
        CAPTURED["history"] = history
        return "  پاسخ آزمایشی دستیار  "

    @classmethod
    def reset(cls):
        CAPTURED.clear()


@pytest.fixture()
def fake_provider(monkeypatch):
    FakeProvider.reset()
    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    return FakeProvider


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"چت {suffix}"}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


# --- provider wire format (OpenAI-compatible, mocked HTTP) ---


def test_provider_sends_openai_compatible_request(monkeypatch):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "پاسخ مدل"}}]},
        )

    provider = OpenAICompatibleProvider(
        base_url="https://ai.test/v1/",
        api_key="test-key",
        model="test-model",
        timeout=5.0,
    )
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=transport, timeout=kwargs.get("timeout")),
    )

    answer = provider.complete(
        system="SYS", user="USR", history=[{"role": "user", "content": "قبل"}]
    )

    assert answer == "پاسخ مدل"
    request = requests[0]
    assert str(request.url) == "https://ai.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "test-model"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert body["messages"][-1] == {"role": "user", "content": "USR"}
    assert {"role": "user", "content": "قبل"} in body["messages"]


def test_provider_maps_errors(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    provider = OpenAICompatibleProvider(
        base_url="https://ai.test/v1", api_key="k", model="m", timeout=5.0
    )
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=transport, timeout=kwargs.get("timeout")),
    )

    with pytest.raises(AIError, match="API key"):
        provider.complete(system="s", user="u")


def test_get_provider_without_key_raises():
    ai.reset_provider_cache()
    monkeypatched = pytest.MonkeyPatch()
    monkeypatched.setattr(get_settings(), "AI_API_KEY", "")
    try:
        with pytest.raises(AIUnavailableError):
            ai.get_provider()
    finally:
        monkeypatched.undo()
        ai.reset_provider_cache()


# --- Gemini native provider (wire format mocked) ---


def _mock_http(monkeypatch, handler):
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=transport, timeout=kwargs.get("timeout")
        ),
    )


def test_gemini_provider_sends_native_request(monkeypatch):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {"text": "خلاصهٔ وضعیت: "},
                                {"text": "دیابت کنترل‌نشده"},
                            ],
                        }
                    }
                ]
            },
        )

    _mock_http(monkeypatch, handler)
    provider = GeminiProvider(api_key="gem-key", model="gemini-2.5-flash", timeout=5.0)

    answer = provider.complete(
        system="SYS",
        user="USR",
        history=[
            {"role": "user", "content": "سؤال قبل"},
            {"role": "assistant", "content": "پاسخ قبل"},
        ],
    )

    assert answer == "خلاصهٔ وضعیت: دیابت کنترل‌نشده"  # parts joined
    request = requests[0]
    assert str(request.url) == (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-2.5-flash:generateContent"
    )
    assert request.headers["x-goog-api-key"] == "gem-key"
    body = json.loads(request.content)
    assert body["system_instruction"] == {"parts": [{"text": "SYS"}]}
    # assistant history turns map to Gemini's "model" role; user stays "user"
    assert body["contents"] == [
        {"role": "user", "parts": [{"text": "سؤال قبل"}]},
        {"role": "model", "parts": [{"text": "پاسخ قبل"}]},
        {"role": "user", "parts": [{"text": "USR"}]},
    ]


def test_gemini_provider_maps_invalid_key(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "API key not valid"}})

    _mock_http(monkeypatch, handler)
    provider = GeminiProvider(api_key="bad", model="gemini-2.5-flash", timeout=5.0)

    with pytest.raises(AIError, match="API key"):
        provider.complete(system="s", user="u")


def test_gemini_provider_maps_quota_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "quota exceeded"}})

    _mock_http(monkeypatch, handler)
    provider = GeminiProvider(api_key="k", model="gemini-2.5-flash", timeout=5.0)

    with pytest.raises(AIError, match="rate limit"):
        provider.complete(system="s", user="u")


def test_provider_dispatch_selects_gemini_with_default_model(monkeypatch):
    ai.reset_provider_cache()
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "AI_API_KEY", "gem-key")
    monkeypatch.setattr(settings, "AI_MODEL", "")
    try:
        provider = ai.get_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-2.5-flash"
    finally:
        ai.reset_provider_cache()


def test_provider_dispatch_openai_default_model(monkeypatch):
    ai.reset_provider_cache()
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai_compatible")
    monkeypatch.setattr(settings, "AI_API_KEY", "k")
    monkeypatch.setattr(settings, "AI_MODEL", "")
    try:
        provider = ai.get_provider()
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.model == "gpt-4o-mini"
    finally:
        ai.reset_provider_cache()


# --- prompt building ---


def test_build_user_message_grounded_and_truncated():
    context = {
        "patient": {"first_name": "علی"},
        "documents": [{"extracted_text": "LONG" * 2000}],
        "voice_notes": [{"transcript": None}],
    }

    message = ai.build_user_message(context, "وضعیت قند خون چطور است؟")

    assert "علی" in message
    assert "وضعیت قند خون" in message
    assert len(message) < 20_000  # long fields are capped
    assert ai.SYSTEM_PROMPT.startswith("You are a clinical decision-support")


# --- API ---


def test_chat_returns_answer_and_grounded_prompt(api_client, make_patient, fake_provider):
    patient = make_patient("۱")
    api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/conditions",
        json={"name": "دیابت نوع ۲"},
    ).raise_for_status()

    response = api_client.post(
        CHAT_URL.format(patient_id=patient["id"]), json={"question": "داروهای بیمار چیست؟"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient_id"] == patient["id"]
    assert body["question"] == "داروهای بیمار چیست؟"
    assert body["answer"] == "پاسخ آزمایشی دستیار"  # trimmed
    assert body["generated_at"]
    # the prompt is grounded in this patient's context
    assert "دیابت نوع ۲" in CAPTURED["user"]
    assert CAPTURED["system"] == ai.SYSTEM_PROMPT


def test_chat_passes_bounded_history(api_client, make_patient, fake_provider):
    patient = make_patient("۲")
    history = [
        {"role": "user", "content": f"سؤال {i}"} for i in range(10)
    ] + [{"role": "assistant", "content": "پاسخ"}]

    api_client.post(
        CHAT_URL.format(patient_id=patient["id"]),
        json={"question": "ادامه", "history": history},
    ).raise_for_status()

    assert len(CAPTURED["history"]) == get_settings().AI_MAX_HISTORY_TURNS


def test_chat_without_key_returns_503(api_client, make_patient, monkeypatch):
    patient = make_patient("۳")
    ai.reset_provider_cache()
    monkeypatch.setattr(get_settings(), "AI_API_KEY", "")
    try:
        response = api_client.post(
            CHAT_URL.format(patient_id=patient["id"]), json={"question": "سلام"}
        )
    finally:
        ai.reset_provider_cache()

    assert response.status_code == 503
    assert response.json()["detail"] == AI_NOT_CONFIGURED_DETAIL


def test_chat_provider_failure_returns_502(api_client, make_patient, monkeypatch):
    patient = make_patient("۴")

    class BrokenProvider:
        def complete(self, **kwargs):
            raise AIError("boom")

    monkeypatch.setattr(ai, "get_provider", lambda: BrokenProvider())

    response = api_client.post(
        CHAT_URL.format(patient_id=patient["id"]), json={"question": "سلام"}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == AI_PROVIDER_ERROR_DETAIL


def test_chat_validations(api_client, make_patient, fake_provider):
    patient = make_patient("۵")
    url = CHAT_URL.format(patient_id=patient["id"])

    empty = api_client.post(url, json={"question": ""})
    assert empty.status_code == 422

    bad_role = api_client.post(
        url, json={"question": "x", "history": [{"role": "system", "content": "y"}]}
    )
    assert bad_role.status_code == 422

    missing = api_client.post(CHAT_URL.format(patient_id=999999), json={"question": "x"})
    assert missing.status_code == 404
    assert missing.json()["detail"] == PATIENT_NOT_FOUND_DETAIL
