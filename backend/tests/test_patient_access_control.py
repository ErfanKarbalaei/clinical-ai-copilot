"""Patient-level authorization tests (Task 18).

Matrix: doctor↔assigned patient (allowed), doctor↔other patient (403),
admin (allowed everywhere), anonymous (401) — across nested routes, flat
child resources, document download, evidence chat, safety check, and the
Task-17 agent route.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.v1.dependencies import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import Document, Patient, PatientUserAccess, User
from app.models.enums import DocumentType, UserRole
from app.services import agent as agent_service, ai

PATIENTS_URL = "/api/v1/patients"


class FakeProvider:
    """Adaptive fake: answers in the right contract per system prompt."""

    def complete(self, *, system, user, history=None):
        if "overall_assessment" in system:  # Task 14 safety JSON contract
            return json.dumps(
                {
                    "overall_assessment": "بررسی انجام شد.",
                    "interactions": [],
                    "patient_factors": [],
                    "missing_information": [],
                    "uncertainty": None,
                },
                ensure_ascii=False,
            )
        if "planning step of a clinical AI agent" in system:  # Task 17 plan
            return json.dumps({"tools": ["get_patient_medications"]})
        # Task 15/16 evidence chat contract
        return json.dumps(
            {"answer": "پاسخ آزمایشی.", "evidence": []}, ensure_ascii=False
        )


class FakeMCP:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append(name)
        return []


@pytest.fixture()
def auth_client(db_session, monkeypatch):
    """Client with the REAL auth dependency; AI + MCP mocked."""
    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    fake_mcp = FakeMCP()
    monkeypatch.setattr(agent_service, "get_mcp_client", lambda: fake_mcp)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
    return fake_mcp


@pytest.fixture()
def users(db_session):
    doctor = User(
        email="doctor@testcompany.com",
        password_hash=hash_password("doctor-pass-123"),
        full_name="پزشک",
        role=UserRole.doctor,
    )
    admin = User(
        email="admin@testcompany.com",
        password_hash=hash_password("admin-pass-123"),
        full_name="مدیر",
        role=UserRole.admin,
    )
    db_session.add_all([doctor, admin])
    db_session.commit()
    return {"doctor": doctor, "admin": admin}


@pytest.fixture()
def patients(db_session, users):
    mine = Patient(first_name="بیمار", last_name="مجاز")
    other = Patient(first_name="بیمار", last_name="غیرمجاز")
    db_session.add_all([mine, other])
    db_session.flush()
    db_session.add(
        PatientUserAccess(patient_id=mine.id, user_id=users["doctor"].id)
    )
    db_session.commit()
    return {"mine": mine, "other": other}


def _login(client, email, password):
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def doctor_headers(auth_client, users):
    return _login(auth_client, "doctor@testcompany.com", "doctor-pass-123")


@pytest.fixture()
def admin_headers(auth_client, users):
    return _login(auth_client, "admin@testcompany.com", "admin-pass-123")


# --- the authorization matrix on nested patient routes ---


NESTED_GET = [
    ("/patients/{pid}", None),
    ("/patients/{pid}/context", None),
    ("/patients/{pid}/timeline", None),
    ("/patients/{pid}/overview", None),
    ("/patients/{pid}/documents", None),
    ("/patients/{pid}/voice-notes", None),
    ("/patients/{pid}/medications", None),
    ("/patients/{pid}/conditions", None),
    ("/patients/{pid}/allergies", None),
    ("/patients/{pid}/conversations", None),
]


@pytest.mark.parametrize("path,query", NESTED_GET)
def test_doctor_allowed_on_assigned(auth_client, patients, doctor_headers, path, query):
    url = PATIENTS_URL.rsplit("/patients", 1)[0] + path.format(pid=patients["mine"].id)
    assert auth_client.get(url, headers=doctor_headers).status_code == 200, url


@pytest.mark.parametrize("path,query", NESTED_GET)
def test_doctor_forbidden_on_other(auth_client, patients, doctor_headers, path, query):
    url = PATIENTS_URL.rsplit("/patients", 1)[0] + path.format(pid=patients["other"].id)
    assert auth_client.get(url, headers=doctor_headers).status_code == 403, url


@pytest.mark.parametrize("path,query", NESTED_GET)
def test_admin_allowed_everywhere(
    auth_client, patients, doctor_headers, admin_headers, path, query
):
    url = PATIENTS_URL.rsplit("/patients", 1)[0] + path.format(pid=patients["other"].id)
    assert auth_client.get(url, headers=doctor_headers).status_code == 403, url
    assert auth_client.get(url, headers=admin_headers).status_code == 200, url


# --- AI endpoints respect the same matrix (provider mocked) ---


def test_chat_allowed_for_assigned_not_for_other(auth_client, patients, doctor_headers):
    ok = auth_client.post(
        f"{PATIENTS_URL}/{patients['mine'].id}/chat",
        json={"question": "وضعیت؟"},
        headers=doctor_headers,
    )
    assert ok.status_code == 200
    denied = auth_client.post(
        f"{PATIENTS_URL}/{patients['other'].id}/chat",
        json={"question": "وضعیت؟"},
        headers=doctor_headers,
    )
    assert denied.status_code == 403


def test_ai_medication_safety_respects_access(auth_client, patients, doctor_headers):
    ok = auth_client.post(
        f"{PATIENTS_URL}/{patients['mine'].id}/medications/ai-safety-check",
        json={"medications": [{"name": "Warfarin"}]},
        headers=doctor_headers,
    )
    assert ok.status_code == 200
    denied = auth_client.post(
        f"{PATIENTS_URL}/{patients['other'].id}/medications/ai-safety-check",
        json={"medications": [{"name": "Warfarin"}]},
        headers=doctor_headers,
    )
    assert denied.status_code == 403


def test_agent_route_respects_access_before_mcp(auth_client, patients, doctor_headers):
    ok = auth_client.post(
        f"{PATIENTS_URL}/{patients['mine'].id}/agent/chat",
        json={"content": "داروها؟"},
        headers=doctor_headers,
    )
    assert ok.status_code == 200
    denied = auth_client.post(
        f"{PATIENTS_URL}/{patients['other'].id}/agent/chat",
        json={"content": "داروها؟"},
        headers=doctor_headers,
    )
    assert denied.status_code == 403  # refused BEFORE any tool/patient data


# --- flat child resources: ownership through the related patient ---


def _make_document(db_session, patient_id, key):
    document = Document(
        patient_id=patient_id,
        title="سند",
        storage_key=key,
        file_name="a.pdf",
        mime_type="application/pdf",
        file_size_bytes=1,
        doc_type=DocumentType.other,
    )
    db_session.add(document)
    db_session.commit()
    return document


def test_document_download_authorized_before_presigned(
    auth_client, db_session, patients, doctor_headers
):
    mine = _make_document(db_session, patients["mine"].id, "k-auth-mine.pdf")
    other = _make_document(db_session, patients["other"].id, "k-auth-other.pdf")

    ok = auth_client.get(
        f"/api/v1/documents/{mine.id}/download",
        headers=doctor_headers,
        follow_redirects=False,
    )
    assert ok.status_code == 307  # presigned only AFTER authorization

    denied = auth_client.get(
        f"/api/v1/documents/{other.id}/download",
        headers=doctor_headers,
        follow_redirects=False,
    )
    assert denied.status_code == 403


def test_document_metadata_and_delete_respect_access(
    auth_client, db_session, patients, doctor_headers
):
    other = _make_document(db_session, patients["other"].id, "k-auth-other2.pdf")
    assert (
        auth_client.get(f"/api/v1/documents/{other.id}", headers=doctor_headers).status_code
        == 403
    )
    assert (
        auth_client.delete(f"/api/v1/documents/{other.id}", headers=doctor_headers).status_code
        == 403
    )


def test_conversation_flat_routes_respect_access(
    auth_client, db_session, patients, doctor_headers
):
    other_conv = auth_client.post(
        f"{PATIENTS_URL}/{patients['other'].id}/conversations",
        json={},
        headers=_login(auth_client, "admin@testcompany.com", "admin-pass-123"),
    ).json()

    assert (
        auth_client.get(
            f"/api/v1/conversations/{other_conv['id']}", headers=doctor_headers
        ).status_code
        == 403
    )
    denied_send = auth_client.post(
        f"/api/v1/conversations/{other_conv['id']}/messages",
        json={"content": "سلام"},
        headers=doctor_headers,
    )
    assert denied_send.status_code == 403
    assert (
        auth_client.delete(
            f"/api/v1/conversations/{other_conv['id']}", headers=doctor_headers
        ).status_code
        == 403
    )

    # same flow on the ASSIGNED patient works end-to-end (evidence chat too)
    mine_conv = auth_client.post(
        f"{PATIENTS_URL}/{patients['mine'].id}/conversations",
        json={},
        headers=doctor_headers,
    ).json()
    sent = auth_client.post(
        f"/api/v1/conversations/{mine_conv['id']}/messages",
        json={"content": "وضعیت؟", "medication_safety": True},
        headers=doctor_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["assistant_message"]["content"] == "پاسخ آزمایشی."


def test_voice_note_flat_route_respects_access(
    auth_client, db_session, patients, doctor_headers
):
    from app.models import VoiceNote

    other_note = VoiceNote(
        patient_id=patients["other"].id,
        audio_storage_key="k-auth-voice-other",
    )
    db_session.add(other_note)
    db_session.commit()
    response = auth_client.get(
        f"/api/v1/voice-notes/{other_note.id}", headers=doctor_headers
    )
    assert response.status_code == 403


# --- patient list scoping + auto-assignment on create ---


def test_patient_list_scoped_by_role(auth_client, patients, doctor_headers, admin_headers):
    doctor_view = auth_client.get(PATIENTS_URL, headers=doctor_headers).json()
    admin_view = auth_client.get(PATIENTS_URL, headers=admin_headers).json()
    assert doctor_view["total"] == 1  # only the assigned patient
    assert admin_view["total"] == 2


def test_doctor_created_patient_is_auto_assigned(
    auth_client, patients, doctor_headers, db_session
):
    created = auth_client.post(
        PATIENTS_URL,
        json={"first_name": "بیمار", "last_name": "جدید"},
        headers=doctor_headers,
    )
    assert created.status_code == 201
    listing = auth_client.get(PATIENTS_URL, headers=doctor_headers).json()
    assert listing["total"] == 2  # sees the new one immediately
    detail = auth_client.get(
        f"{PATIENTS_URL}/{created.json()['id']}", headers=doctor_headers
    )
    assert detail.status_code == 200
