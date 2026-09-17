"""Agent API tests — Gemini and the MCP client fully mocked."""

import json

import pytest

from app.services import agent as agent_service, ai

PATIENTS_URL = "/api/v1/patients"
AGENT_CHAT_URL = "/api/v1/patients/{patient_id}/agent/chat"
CHAT_URL = "/api/v1/patients/{patient_id}/chat"


def _plan(tools: list[str]) -> str:
    return json.dumps({"tools": tools})


class FakeAgentProvider:
    """Planner response first, final answer second."""

    def __init__(self):
        self.responses: list[str] = []
        self.calls: list[dict] = []

    def complete(self, *, system, user, history=None):
        self.calls.append({"system": system, "user": user})
        return self.responses.pop(0)


class FakeMCPClient:
    def __init__(self, results: dict | None = None, error: Exception | None = None):
        self.results = results or {}
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name, arguments):
        if self.error is not None:
            raise self.error
        self.calls.append((name, arguments))
        return self.results.get(
            name, [{"note": "empty"}]
        )


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"Agent {suffix}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture()
def fake_agent(monkeypatch):
    provider = FakeAgentProvider()
    monkeypatch.setattr(ai, "get_provider", lambda: provider)

    mcp = FakeMCPClient()
    monkeypatch.setattr(agent_service, "get_mcp_client", lambda: mcp)
    return provider, mcp


def _ask(api_client, patient_id: int, content: str):
    return api_client.post(
        AGENT_CHAT_URL.format(patient_id=patient_id), json={"content": content}
    )


# --- tool selection ---


def test_medication_question_selects_medication_tool(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_medications"]),
        "بیمار Metformin مصرف می‌کند.",
    ]
    mcp.results = {"get_patient_medications": [{"medication": {"name": "Metformin 500"}}]}
    patient = make_patient("۱")

    response = _ask(api_client, patient["id"], "داروهای فعلی بیمار چیست؟")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "بیمار Metformin مصرف می‌کند."
    assert body["tools_used"] == [
        {"name": "get_patient_medications", "label": "داروهای بیمار"}
    ]
    # patient scope injected by the backend, never by the model
    assert mcp.calls == [("get_patient_medications", {"patient_id": patient["id"]})]
    # answerer got the real tool data
    assert "Metformin" in provider.calls[1]["user"]


def test_lab_question_selects_lab_tool(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_labs"]),
        "آخرین HbA1c برابر ۸.۲ است.",
    ]
    mcp.results = {"get_patient_labs": [{"test_name": "HbA1c", "value": "8.2"}]}

    response = _ask(api_client, make_patient("۲")["id"], "آخرین آزمایش‌های بیمار چیست؟")

    assert response.status_code == 200
    assert mcp.calls[0][0] == "get_patient_labs"


def test_context_question_selects_context_tool(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_context"]),
        "خلاصهٔ وضعیت…",
    ]
    mcp.results = {"get_patient_context": {"patient": {"id": 1}, "medications": []}}

    response = _ask(api_client, make_patient("۳")["id"], "وضعیت کلی بیمار چیست؟")

    assert response.status_code == 200
    assert mcp.calls[0][0] == "get_patient_context"


def test_document_question_selects_document_tool(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_documents"]),
        "دو سند در پرونده وجود دارد.",
    ]
    mcp.results = {"get_patient_documents": [{"title": "آزمایش خون"}]}

    response = _ask(api_client, make_patient("۴")["id"], "چه اسنادی در پرونده هست؟")

    assert response.status_code == 200
    assert mcp.calls[0][0] == "get_patient_documents"


def test_multi_tool_question(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_medications", "get_patient_labs", "get_patient_context"]),
        "تحلیل ترکیبی کامل.",
    ]
    mcp.results = {
        "get_patient_medications": [{"medication": {"name": "Metformin"}}],
        "get_patient_labs": [{"test_name": "HbA1c", "value": "8.2"}],
        "get_patient_context": {"patient": {"id": 1}},
    }
    patient = make_patient("۵")

    response = _ask(
        api_client, patient["id"], "با توجه به بیماری‌ها، داروها و آزمایش‌ها وضعیت را توضیح بده."
    )

    assert response.status_code == 200
    assert [name for name, _ in mcp.calls] == [
        "get_patient_medications", "get_patient_labs", "get_patient_context",
    ]
    assert len(response.json()["tools_used"]) == 3


def test_unknown_tool_names_dropped(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        json.dumps({"tools": ["run_sql", "delete_patient", "get_patient_labs"]}),
        "پاسخ.",
    ]
    patient = make_patient("۶")

    response = _ask(api_client, patient["id"], "آزمایش‌ها؟")

    assert response.status_code == 200
    assert [name for name, _ in mcp.calls] == ["get_patient_labs"]  # only known tools


def test_direct_answer_without_tools(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = ['{"answer": "پاسخ عمومی مستقیم."}']

    response = _ask(api_client, make_patient("۷")["id"], "متفورمین چیست؟")

    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ عمومی مستقیم."
    assert response.json()["tools_used"] == []
    assert mcp.calls == []


# --- failure handling (never fabricate) ---


def test_mcp_unavailable_is_clean_503(api_client, make_patient, monkeypatch):
    provider = FakeAgentProvider()
    provider.responses = [_plan(["get_patient_labs"]), "x"]
    monkeypatch.setattr(ai, "get_provider", lambda: provider)

    def unavailable():
        raise agent_service.MCPUnavailableError("mcp down")

    monkeypatch.setattr(agent_service, "get_mcp_client", unavailable)

    response = _ask(api_client, make_patient("۸")["id"], "آزمایش‌ها؟")

    assert response.status_code == 503
    assert "MCP" in response.json()["detail"] or "ابزار" in response.json()["detail"]


def test_mcp_tool_failure_is_502_no_fake_data(api_client, make_patient, monkeypatch):
    provider = FakeAgentProvider()
    provider.responses = [_plan(["get_patient_labs"]), "x"]
    monkeypatch.setattr(ai, "get_provider", lambda: provider)
    monkeypatch.setattr(
        agent_service, "get_mcp_client", lambda: FakeMCPClient(error=agent_service.MCPToolError("tool failed"))
    )

    response = _ask(api_client, make_patient("۹")["id"], "آزمایش‌ها؟")

    assert response.status_code == 502


def test_gemini_failure_is_502(api_client, make_patient, fake_agent):
    provider, _ = fake_agent
    provider.responses = []  # complete() will fail below

    class Broken:
        def complete(self, **kwargs):
            raise ai.AIError("provider down")

    import app.services.agent as svc
    monkeypatch_holder = pytest.MonkeyPatch()
    monkeypatch_holder.setattr(ai, "get_provider", lambda: Broken())
    try:
        response = _ask(api_client, make_patient("۱۰")["id"], "سلام")
        assert response.status_code == 502
    finally:
        monkeypatch_holder.undo()


def test_gemini_unconfigured_is_503(api_client, make_patient, monkeypatch):
    def unavailable():
        raise ai.AIUnavailableError("no key")

    monkeypatch.setattr(ai, "get_provider", unavailable)
    response = _ask(api_client, make_patient("۱۱")["id"], "سلام")
    assert response.status_code == 503


def test_malformed_planner_response_is_502(api_client, make_patient, fake_agent):
    provider, _ = fake_agent
    provider.responses = ["این یک برنامه نیست."]

    response = _ask(api_client, make_patient("۱۲")["id"], "داروها؟")

    assert response.status_code == 502


def test_empty_tool_result_still_answers(api_client, make_patient, fake_agent):
    provider, mcp = fake_agent
    provider.responses = [
        _plan(["get_patient_labs"]),
        "در پرونده آزمایشی ثبت نشده است.",
    ]
    mcp.results = {"get_patient_labs": []}

    response = _ask(api_client, make_patient("۱۳")["id"], "آزمایش‌ها؟")

    assert response.status_code == 200
    assert response.json()["answer"] == "در پرونده آزمایشی ثبت نشده است."


def test_unknown_patient_404(api_client, fake_agent):
    provider, _ = fake_agent
    provider.responses = [_plan(["get_patient"]), "x"]
    response = _ask(api_client, 999999, "سلام")
    assert response.status_code == 404


def test_empty_content_422(api_client, make_patient, fake_agent):
    provider, _ = fake_agent
    provider.responses = []
    response = api_client.post(
        AGENT_CHAT_URL.format(patient_id=make_patient("۱۴")["id"]),
        json={"content": ""},
    )
    assert response.status_code == 422


# --- coexistence: normal chat paths keep working ---


def test_normal_stateless_chat_still_works(api_client, make_patient, monkeypatch):
    provider = FakeAgentProvider()
    provider.responses = ["پاسخ چت معمولی."]
    monkeypatch.setattr(ai, "get_provider", lambda: provider)

    response = api_client.post(
        CHAT_URL.format(patient_id=make_patient("۱۵")["id"]),
        json={"question": "سلام"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ چت معمولی."


def test_persistent_chat_still_works_beside_agent(api_client, make_patient, fake_agent):
    provider, _ = fake_agent
    provider.responses = [
        json.dumps({"answer": "خلاصهٔ وضعیت", "evidence": []})  # T16 evidence format
    ]
    patient = make_patient("۱۶")
    conversation = api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/conversations", json={}
    ).json()

    response = api_client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "وضعیت؟", "medication_safety": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["assistant_message"]["content"] == "خلاصهٔ وضعیت"
