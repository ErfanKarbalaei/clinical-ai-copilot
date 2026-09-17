"""Persistent-conversation tests (provider mocked — no real LLM calls)."""

import pytest

from sqlalchemy import select

from app.models import Conversation, ConversationMessage
from app.schemas.conversation import DEFAULT_CONVERSATION_TITLE
from app.services import ai

PATIENTS_URL = "/api/v1/patients"
CONVERSATIONS_NESTED_URL = "/api/v1/patients/{patient_id}/conversations"
CONVERSATION_URL = "/api/v1/conversations/{conversation_id}"
MESSAGES_URL = "/api/v1/conversations/{conversation_id}/messages"

CAPTURED: dict = {}


class FakeProvider:
    def complete(self, *, system, user, history=None):
        CAPTURED["system"] = system
        CAPTURED["user"] = user
        CAPTURED["history"] = history
        return "پاسخ آزمایشی دستیار."


@pytest.fixture()
def fake_provider(monkeypatch):
    CAPTURED.clear()
    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    return FakeProvider


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"گفتگو {suffix}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _make_conversation(api_client, patient_id: int, title: str | None = None) -> dict:
    response = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient_id),
        json={"title": title} if title else {},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _send(api_client, conversation_id: int, content: str, safety: bool = False):
    return api_client.post(
        MESSAGES_URL.format(conversation_id=conversation_id),
        json={"content": content, "medication_safety": safety},
    )


# --- conversation CRUD ---


def test_create_conversation_default_title(api_client, make_patient):
    patient = make_patient("۱")
    body = _make_conversation(api_client, patient["id"])
    assert body["patient_id"] == patient["id"]
    assert body["title"] == DEFAULT_CONVERSATION_TITLE  # گفتگوی جدید
    assert body["created_at"] and body["updated_at"]


def test_create_conversation_custom_title(api_client, make_patient):
    patient = make_patient("۲")
    body = _make_conversation(api_client, patient["id"], title="مشاوره دارویی")
    assert body["title"] == "مشاوره دارویی"


def test_create_conversation_unknown_patient_404(api_client):
    response = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=999999), json={}
    )
    assert response.status_code == 404


def test_list_conversations_most_recently_updated_first(api_client, db_session, make_patient):
    patient = make_patient("۳")
    first = _make_conversation(api_client, patient["id"], title="اول")
    second = _make_conversation(api_client, patient["id"], title="دوم")

    listing = api_client.get(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"])
    ).json()
    assert [item["id"] for item in listing] == [second["id"], first["id"]]

    # bumping the first conversation moves it back to the top
    row = db_session.get(Conversation, first["id"])
    from datetime import datetime, timedelta, timezone

    row.updated_at = datetime.now(timezone.utc) + timedelta(seconds=5)
    db_session.commit()

    listing = api_client.get(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"])
    ).json()
    assert [item["id"] for item in listing] == [first["id"], second["id"]]


def test_get_conversation_with_messages_ordered(api_client, make_patient, fake_provider):
    patient = make_patient("۴")
    conversation = _make_conversation(api_client, patient["id"])

    _send(api_client, conversation["id"], "پرسش اول")
    _send(api_client, conversation["id"], "پرسش دوم")

    detail = api_client.get(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    ).json()
    roles = [message["role"] for message in detail["messages"]]
    contents = [message["content"] for message in detail["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert contents == ["پرسش اول", "پاسخ آزمایشی دستیار.", "پرسش دوم", "پاسخ آزمایشی دستیار."]
    ids = [message["id"] for message in detail["messages"]]
    assert ids == sorted(ids)  # oldest first


def test_get_unknown_conversation_404(api_client):
    response = api_client.get(CONVERSATION_URL.format(conversation_id=999999))
    assert response.status_code == 404
    assert response.json()["detail"] == "گفتگو یافت نشد."


def test_delete_conversation_cascades_messages(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۵")
    conversation = _make_conversation(api_client, patient["id"])
    _send(api_client, conversation["id"], "پیام")

    response = api_client.delete(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    )
    assert response.status_code == 204
    assert api_client.get(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    ).status_code == 404
    remaining = db_session.scalars(select(ConversationMessage)).all()
    assert remaining == []  # messages removed with the conversation


# --- sending messages (AI integration) ---


def test_send_message_persists_user_and_assistant(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۶")
    conversation = _make_conversation(api_client, patient["id"])

    response = _send(api_client, conversation["id"], "وضعیت بیمار چطور است؟")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "وضعیت بیمار چطور است؟"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] == "پاسخ آزمایشی دستیار."

    persisted = db_session.scalars(select(ConversationMessage)).all()
    assert len(persisted) == 2  # both rows really in the database


def test_first_message_derives_deterministic_title(api_client, make_patient, fake_provider):
    patient = make_patient("۷")
    conversation = _make_conversation(api_client, patient["id"])  # default title
    _send(api_client, conversation["id"], "آیا این بیمار وارفارین می‌تواند مصرف کند؟")

    detail = api_client.get(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    ).json()
    assert detail["title"] == "آیا این بیمار وارفارین می‌تواند مصرف کند؟"

    # a custom title is never overwritten
    custom = _make_conversation(api_client, patient["id"], title="عنوان ثابت")
    _send(api_client, custom["id"], "پرسش دیگر")
    detail = api_client.get(
        CONVERSATION_URL.format(conversation_id=custom["id"])
    ).json()
    assert detail["title"] == "عنوان ثابت"


def test_patient_context_and_history_passed_to_ai(api_client, make_patient, fake_provider):
    patient = make_patient("۸")
    api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/conditions", json={"name": "دیابت نوع ۲"}
    )
    conversation = _make_conversation(api_client, patient["id"])

    _send(api_client, conversation["id"], "پرسش اول")
    assert CAPTURED["history"] == []  # first exchange: no prior history
    assert CAPTURED["user"].startswith("Patient record (JSON):")  # Task 9 context
    assert "دیابت نوع ۲" in CAPTURED["user"]
    assert "پرسش اول" in CAPTURED["user"]

    _send(api_client, conversation["id"], "پرسش دوم")
    assert CAPTURED["history"] == [
        {"role": "user", "content": "پرسش اول"},
        {"role": "assistant", "content": "پاسخ آزمایشی دستیار."},
    ]
    assert "پرسش دوم" in CAPTURED["user"]  # current message sent separately


def test_history_is_capped(api_client, make_patient, fake_provider):
    patient = make_patient("۹")
    conversation = _make_conversation(api_client, patient["id"])

    for index in range(12):  # 24 persisted messages
        _send(api_client, conversation["id"], f"پرسش {index}")

    assert len(CAPTURED["history"]) == 20
    # 22 prior messages → the 2 oldest (پرسش 0 و پاسخ آن) are dropped
    assert CAPTURED["history"][0]["content"] == "پرسش 1"
    assert CAPTURED["history"][-1]["content"] == "پاسخ آزمایشی دستیار."


def test_medication_safety_flag_switches_prompt(api_client, make_patient, fake_provider):
    from app.services.ai_medication_safety import MEDICATION_SAFETY_CHAT_PROMPT

    patient = make_patient("۱۰")
    conversation = _make_conversation(api_client, patient["id"])

    _send(api_client, conversation["id"], "وارفارین تجویز کنم؟", safety=True)
    assert CAPTURED["system"] == MEDICATION_SAFETY_CHAT_PROMPT

    _send(api_client, conversation["id"], "پرسش عادی")
    assert CAPTURED["system"] == ai.SYSTEM_PROMPT


def test_ai_failure_keeps_user_message_without_fake_assistant(
    api_client, db_session, make_patient, monkeypatch
):
    patient = make_patient("۱۱")
    conversation = _make_conversation(api_client, patient["id"])

    class FailingProvider:
        def complete(self, *, system, user, history=None):
            raise ai.AIError("provider down")

    monkeypatch.setattr(ai, "get_provider", lambda: FailingProvider())

    response = _send(api_client, conversation["id"], "پرسش مهم")

    assert response.status_code == 502
    messages = db_session.scalars(select(ConversationMessage)).all()
    assert len(messages) == 1  # only the user message — nothing fabricated
    assert messages[0].content == "پرسش مهم"


def test_ai_unconfigured_503_user_message_still_persisted(
    api_client, db_session, make_patient, monkeypatch
):
    patient = make_patient("۱۲")
    conversation = _make_conversation(api_client, patient["id"])

    def unavailable():
        raise ai.AIUnavailableError("AI_API_KEY is not configured")

    monkeypatch.setattr(ai, "get_provider", unavailable)

    response = _send(api_client, conversation["id"], "پرسش")

    assert response.status_code == 503
    assert len(db_session.scalars(select(ConversationMessage)).all()) == 1


def test_send_message_validations(api_client, make_patient, fake_provider):
    patient = make_patient("۱۳")
    conversation = _make_conversation(api_client, patient["id"])

    empty = _send(api_client, conversation["id"], "")
    assert empty.status_code == 422

    missing_conversation = api_client.post(
        MESSAGES_URL.format(conversation_id=999999), json={"content": "سلام"}
    )
    assert missing_conversation.status_code == 404


def test_existing_stateless_chat_still_works(api_client, make_patient, fake_provider):
    """Task 10 endpoint remains untouched and functional alongside Task 15."""
    patient = make_patient("۱۴")
    response = api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/chat",
        json={"question": "خلاصهٔ وضعیت؟"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ آزمایشی دستیار."
    assert CAPTURED["system"] == ai.SYSTEM_PROMPT
