"""Evidence & source-document tests (provider mocked — no real LLM calls).

Task 16: stable evidence ids from REAL records, backend-side validation of
model-claimed evidence, document resolution via the existing secure
endpoint, persistence + reload. No external medical literature involved.
"""

import json

import pytest
from sqlalchemy import select

from app.models import ConversationMessage
from app.services import ai, evidence
from app.services.evidence import (
    EVIDENCE_CHAT_SYSTEM_PROMPT,
    EVIDENCE_SAFETY_SYSTEM_PROMPT,
    build_evidence_index,
    parse_evidence_answer,
    validate_evidence,
)

PATIENTS_URL = "/api/v1/patients"
CONVERSATIONS_NESTED_URL = "/api/v1/patients/{patient_id}/conversations"
CONVERSATION_URL = "/api/v1/conversations/{conversation_id}"
MESSAGES_URL = "/api/v1/conversations/{conversation_id}/messages"

CAPTURED: dict = {}


def _ai_answer(items: list[str], answer: str = "پاسخ مبتنی بر پرونده.") -> str:
    return json.dumps({"answer": answer, "evidence": items}, ensure_ascii=False)


class FakeProvider:
    response = _ai_answer(["MED-1"])

    def complete(self, *, system, user, history=None):
        CAPTURED["system"] = system
        CAPTURED["user"] = user
        CAPTURED["history"] = history
        return FakeProvider.response


@pytest.fixture()
def fake_provider(monkeypatch):
    CAPTURED.clear()
    FakeProvider.response = _ai_answer(["MED-1"])
    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    return FakeProvider


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"شواهد {suffix}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _seed_records(api_client, patient_id: int) -> dict:
    """Real records through the real APIs; returns their ids."""
    medication = api_client.post(
        f"{PATIENTS_URL}/{patient_id}/medications",
        json={"medication_name": "Metformin 500", "dosage": "500 mg"},
    ).json()
    condition = api_client.post(
        f"{PATIENTS_URL}/{patient_id}/conditions", json={"name": "دیابت نوع ۲"}
    ).json()
    allergy = api_client.post(
        f"{PATIENTS_URL}/{patient_id}/allergies",
        json={"allergen": "Penicillin", "severity": "severe"},
    ).json()
    return {
        "medication": medication,
        "condition": condition,
        "allergy": allergy,
    }


def _send(api_client, conversation_id: int, content: str, safety: bool = False):
    return api_client.post(
        MESSAGES_URL.format(conversation_id=conversation_id),
        json={"content": content, "medication_safety": safety},
    )


# --- evidence index / context annotation (real DB ids only) ---


def test_evidence_index_uses_real_record_ids(api_client, db_session, make_patient):
    patient = make_patient("۱")
    records = _seed_records(api_client, patient["id"])

    from app.services.patient_context import build_patient_context
    from app.models import Patient as PatientModel

    context = build_patient_context(db_session, db_session.get(PatientModel, patient["id"]))
    index = build_evidence_index(context.model_dump())

    assert f"MED-{records['medication']['id']}" in index
    assert f"COND-{records['condition']['id']}" in index
    assert f"ALLERGY-{records['allergy']['id']}" in index
    med = index[f"MED-{records['medication']['id']}"]
    assert med["source_type"] == "medication"
    assert "Metformin" in med["description"]


def test_evidence_ids_are_annotated_into_the_ai_context(
    api_client, make_patient, fake_provider
):
    patient = make_patient("۲")
    records = _seed_records(api_client, patient["id"])
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()

    _send(api_client, conversation["id"], "داروهای بیمار چیست؟")

    user_message = CAPTURED["user"]
    assert f'"evidence_id": "MED-{records["medication"]["id"]}"' in user_message
    assert "NEVER invent" in CAPTURED["system"]  # evidence rules present
    assert "Patient record (JSON):" in user_message  # still the Task-9 context


# --- validation: never trust the model ---


def test_valid_evidence_accepted_and_enriched(api_client, make_patient, fake_provider):
    patient = make_patient("۳")
    records = _seed_records(api_client, patient["id"])
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    med_id = f"MED-{records['medication']['id']}"
    FakeProvider.response = _ai_answer([med_id])

    response = _send(api_client, conversation["id"], "پرسش")
    body = response.json()

    assert response.status_code == 200
    assert len(body["assistant_message"]["evidence"]) == 1
    item = body["assistant_message"]["evidence"][0]
    assert item["source_id"] == med_id
    assert item["source_type"] == "medication"
    assert "Metformin" in item["description"]
    assert item["document_id"] is None  # meds have no source document


def test_unknown_and_fabricated_evidence_dropped(api_client, make_patient, fake_provider):
    patient = make_patient("۴")
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    FakeProvider.response = _ai_answer(
        ["LAB-999", "https://minio.test/patients/1/x.pdf", "PMID:12345", "MED-42"]
    )

    response = _send(api_client, conversation["id"], "پرسش")

    evidence_items = response.json()["assistant_message"]["evidence"]
    assert evidence_items == []  # nothing valid in this empty-context patient


def test_cross_patient_evidence_dropped(api_client, make_patient, fake_provider):
    """A source id from ANOTHER patient must never be exposed here."""
    patient_a = make_patient("۵")
    patient_b = make_patient("۶")
    b_records = _seed_records(api_client, patient_b["id"])
    conversation_a = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient_a["id"]), json={}
    ).json()
    FakeProvider.response = _ai_answer([f"MED-{b_records['medication']['id']}"])

    response = _send(api_client, conversation_a["id"], "پرسش")

    assert response.json()["assistant_message"]["evidence"] == []


def test_validate_evidence_unit():
    index = {
        "DOC-7": {
            "source_type": "document",
            "record_id": 7,
            "description": "آزمایش خون",
            "document_id": 7,
        }
    }
    items = validate_evidence(["DOC-7", "DOC-7", "LAB-1", ""], index)
    assert [item.source_id for item in items] == ["DOC-7"]
    assert items[0].document_id == 7


def test_parse_evidence_answer_structured_and_prose():
    answer, ids = parse_evidence_answer(
        '```json\n{"answer": "سلام", "evidence": ["MED-1"]}\n```'
    )
    assert answer == "سلام"
    assert ids == ["MED-1"]

    # malformed → prose fallback, NO evidence, nothing fabricated
    answer, ids = parse_evidence_answer("این یک پاسخ متنی ساده است.")
    assert answer == "این یک پاسخ متنی ساده است."
    assert ids == []

    answer, ids = parse_evidence_answer('{"evidence": ["MED-1"]}')  # no answer key
    assert ids == []


# --- document-backed evidence (original source access) ---


def test_document_evidence_resolves_and_link_is_the_existing_endpoint(
    api_client, db_session, make_patient, fake_provider
):
    from app.models import Document
    from app.models.enums import DocumentType, ExtractionStatus

    patient = make_patient("۷")
    document = Document(
        patient_id=patient["id"],
        title="آزمایش خون مبلغ‌شده",
        storage_key="patients/1/documents/fake-evidence.pdf",
        file_name="lab.pdf",
        mime_type="application/pdf",
        file_size_bytes=128,
        doc_type=DocumentType.lab_report,
        extraction_status=ExtractionStatus.completed,
        extracted_text="HbA1c 8.2",
    )
    db_session.add(document)
    db_session.commit()
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    FakeProvider.response = _ai_answer([f"DOC-{document.id}"])

    response = _send(api_client, conversation["id"], "آخرین HbA1c؟")
    item = response.json()["assistant_message"]["evidence"][0]

    assert item["source_id"] == f"DOC-{document.id}"
    assert item["source_type"] == "document"
    assert item["document_id"] == document.id
    assert "url" not in item  # no URLs in the evidence payload

    # the original file is served by the EXISTING secure endpoint (307 →
    # short-lived presigned URL; never followed here — the object is fake)
    download = api_client.get(
        f"/api/v1/documents/{document.id}/download", follow_redirects=False
    )
    assert download.status_code == 307
    assert "X-Amz-Signature" in download.headers["location"]


def test_lab_evidence_carries_real_source_document(
    api_client, db_session, make_patient, fake_provider
):
    from app.models import Document, LabResult
    from app.models.enums import DocumentType, ExtractionStatus

    patient = make_patient("۸")
    document = Document(
        patient_id=patient["id"],
        title="گزارش آزمایش",
        storage_key="patients/1/documents/fake-lab.pdf",
        file_name="lab.pdf",
        mime_type="application/pdf",
        file_size_bytes=128,
        doc_type=DocumentType.lab_report,
        extraction_status=ExtractionStatus.completed,
    )
    db_session.add(document)
    db_session.flush()
    lab = LabResult(
        patient_id=patient["id"],
        document_id=document.id,  # the REAL existing FK
        test_name="HbA1c",
        value="8.2",
        unit="%",
    )
    db_session.add(lab)
    db_session.commit()
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    FakeProvider.response = _ai_answer([f"LAB-{lab.id}"])

    response = _send(api_client, conversation["id"], "HbA1c چقدر است؟")
    item = response.json()["assistant_message"]["evidence"][0]

    assert item["source_id"] == f"LAB-{lab.id}"
    assert item["source_type"] == "lab"
    assert "HbA1c" in item["description"]
    assert item["document_id"] == document.id  # real relationship surfaced


# --- persistence + reload (no URLs ever stored) ---


def test_evidence_persists_and_survives_reload(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۹")
    records = _seed_records(api_client, patient["id"])
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    med_id = f"MED-{records['medication']['id']}"
    FakeProvider.response = _ai_answer([med_id])

    _send(api_client, conversation["id"], "پرسش اول")

    message_id = db_session.scalars(
        select(ConversationMessage.id)
        .where(ConversationMessage.conversation_id == conversation["id"])
        .order_by(ConversationMessage.id.desc())
    ).first()
    row = db_session.get(ConversationMessage, message_id)
    assert row.evidence and row.evidence[0]["source_id"] == med_id
    assert "url" not in row.evidence[0]  # temporary URLs are NEVER persisted

    reloaded = api_client.get(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    ).json()
    assistant = [m for m in reloaded["messages"] if m["role"] == "assistant"][-1]
    assert assistant["evidence"][0]["source_id"] == med_id


def test_old_messages_without_evidence_still_render(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۱۰")
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    # pre-Task-16 style message (no evidence column value)
    db_session.add(
        ConversationMessage(
            conversation_id=conversation["id"],
            role="assistant",
            content="پاسخ قدیمی",
        )
    )
    db_session.commit()

    detail = api_client.get(
        CONVERSATION_URL.format(conversation_id=conversation["id"])
    ).json()
    old = [m for m in detail["messages"] if m["content"] == "پاسخ قدیمی"][0]
    assert old["evidence"] == []


# --- medication safety mode + prompts ---


def test_safety_mode_uses_evidence_safety_prompt(api_client, make_patient, fake_provider):
    patient = make_patient("۱۱")
    records = _seed_records(api_client, patient["id"])
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    FakeProvider.response = _ai_answer([f"MED-{records['medication']['id']}"])

    _send(api_client, conversation["id"], "وارفارین تجویز کنم؟", safety=True)

    assert CAPTURED["system"] == EVIDENCE_SAFETY_SYSTEM_PROMPT
    assert "تداخل احتمالی" in CAPTURED["system"]  # Task 14 rules intact
    assert "NEVER invent" in CAPTURED["system"]


def test_prompts_compose_existing_ones():
    assert ai.SYSTEM_PROMPT in EVIDENCE_CHAT_SYSTEM_PROMPT
    from app.services.ai_medication_safety import MEDICATION_SAFETY_CHAT_PROMPT

    assert MEDICATION_SAFETY_CHAT_PROMPT in EVIDENCE_SAFETY_SYSTEM_PROMPT
    for prompt in (EVIDENCE_CHAT_SYSTEM_PROMPT, EVIDENCE_SAFETY_SYSTEM_PROMPT):
        assert "NEVER output URLs" in prompt
        assert "PubMed" in prompt


# --- compatibility: Task 10 old chat + plain conversations keep working ---


def test_task10_stateless_chat_unchanged(api_client, make_patient, fake_provider):
    patient = make_patient("۱۲")
    FakeProvider.response = "پاسخ متنی ساده."  # old endpoint: plain text answer
    response = api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/chat", json={"question": "سلام"}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ متنی ساده."


def test_prose_answer_falls_back_without_evidence(api_client, make_patient, fake_provider):
    patient = make_patient("۱۳")
    conversation = api_client.post(
        CONVERSATIONS_NESTED_URL.format(patient_id=patient["id"]), json={}
    ).json()
    FakeProvider.response = "پاسخ نثر ساده بدون JSON."

    response = _send(api_client, conversation["id"], "پرسش")

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["content"] == "پاسخ نثر ساده بدون JSON."
    assert body["assistant_message"]["evidence"] == []
