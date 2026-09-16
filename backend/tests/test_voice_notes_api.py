"""Voice-note API tests (require PostgreSQL; storage + STT are faked)."""

import pytest
from sqlalchemy import select

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.api.v1.routes import voice_notes as voice_notes_routes
from app.api.v1.routes.voice_notes import (
    INVALID_AUDIO_TYPE_DETAIL,
    VOICE_NOTE_NOT_FOUND_DETAIL,
)
from app.models import ClinicalEvent, ClinicalNote
from app.services import ai, storage, voice_notes as voice_notes_service
from app.services.stt import SttUnavailableError

PATIENTS_URL = "/api/v1/patients"
VOICE_NOTES_NESTED_URL = "/api/v1/patients/{patient_id}/voice-notes"
VOICE_NOTE_ITEM_URL = "/api/v1/voice-notes/{voice_note_id}"

AUDIO_BYTES = b"FAKE-WEBM-AUDIO-BODY"
AUDIO_FILE = {"file": ("recording.webm", AUDIO_BYTES, "audio/webm")}


@pytest.fixture()
def faked_storage_and_stt(monkeypatch, db_session):
    """Fake storage (records/serves bytes) and a fake Speechmatics."""
    keys: list[str] = []
    deleted: list[str] = []
    stored: dict[str, bytes] = {}
    transcribed: list[bool] = []  # diarize flags per call

    def fake_upload(*, patient_id, file_name, content_type, data, folder="documents"):
        key = f"patients/{patient_id}/{folder}/fake-{len(keys) + 1}-{file_name}"
        keys.append(key)
        stored[key] = data
        return key

    monkeypatch.setattr(storage, "upload_file", fake_upload)
    monkeypatch.setattr(storage, "delete_object", lambda key: deleted.append(key))
    monkeypatch.setattr(
        storage,
        "presigned_download_url",
        lambda key, expires=None: f"http://minio.test/{key}?sig=fake",
    )
    monkeypatch.setattr(storage, "get_object_bytes", lambda key: stored[key])

    def fake_transcribe(*, data, file_name, mime_type, language="fa", diarize=False):
        transcribed.append(diarize)
        if language != "fa":
            raise AssertionError("expected Persian (fa) transcription")
        if diarize:
            return "S1: سلام\nS2: سلام، حال شما چطور است؟"
        return "بیمار سابقه دیابت نوع دو دارد و متفورمین مصرف می‌کند."

    monkeypatch.setattr(
        "app.services.voice_notes.stt.transcribe_audio", fake_transcribe
    )
    # deterministic regardless of the developer's .env: AI cleanup never runs
    # in these tests (dedicated cleanup tests fake the provider instead)
    def unavailable_provider():
        raise ai.AIUnavailableError("AI_API_KEY is not configured")

    monkeypatch.setattr(ai, "get_provider", unavailable_provider)
    # run the real pipeline against the isolated test session
    monkeypatch.setattr(
        voice_notes_routes,
        "process_voice_note",
        lambda vn_id: voice_notes_service.process_voice_note(vn_id, db=db_session),
    )
    return {"keys": keys, "deleted": deleted, "transcribed": transcribed}


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"صوت {suffix}"}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _upload(api_client, patient_id: int, files=None, data=None):
    return api_client.post(
        VOICE_NOTES_NESTED_URL.format(patient_id=patient_id),
        files=files or AUDIO_FILE,
        data=data or {},
    )


# --- upload + background transcription ---


def test_upload_then_transcribes_physician_note(api_client, make_patient, faked_storage_and_stt):
    patient = make_patient("۱")

    created = _upload(
        api_client,
        patient["id"],
        data={"title": "یادداشت صوتی ویزیت", "duration_seconds": "42"},
    ).json()
    assert created["transcription_status"] == "pending"  # task runs after response

    final = api_client.get(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"])
    ).json()
    assert final["transcription_status"] == "completed"
    assert "متفورمین" in final["transcript"]
    assert final["conversation_type"] == "physician_note"
    assert final["duration_seconds"] == 42
    assert final["language"] == "fa"
    assert faked_storage_and_stt["transcribed"] == [False]  # no diarization


def test_upload_doctor_patient_conversation_diarizes(
    api_client, make_patient, faked_storage_and_stt
):
    patient = make_patient("۲")

    created = _upload(
        api_client,
        patient["id"],
        data={"conversation_type": "doctor_patient"},
    ).json()

    final = api_client.get(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"])
    ).json()
    assert final["conversation_type"] == "doctor_patient"
    assert "S1:" in final["transcript"] and "S2:" in final["transcript"]
    assert faked_storage_and_stt["transcribed"] == [True]  # diarization requested


def test_upload_creates_timeline_event(api_client, make_patient, faked_storage_and_stt, db_session):
    patient = make_patient("۳")
    created = _upload(api_client, patient["id"], data={"title": "ویزیت صبح"}).json()

    events = db_session.scalars(
        select(ClinicalEvent).where(
            ClinicalEvent.source_type == "voice_note",
            ClinicalEvent.source_id == created["id"],
        )
    ).all()
    assert len(events) == 1
    assert events[0].event_type == "voice_note_recorded"


def test_stt_unavailable_marks_failed(api_client, make_patient, monkeypatch, faked_storage_and_stt):
    patient = make_patient("۴")

    def broken_transcribe(**kwargs):
        raise SttUnavailableError("SPEECHMATICS_API_KEY is not configured")

    monkeypatch.setattr(
        "app.services.voice_notes.stt.transcribe_audio", broken_transcribe
    )

    created = _upload(api_client, patient["id"]).json()

    final = api_client.get(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"])
    ).json()
    assert final["transcription_status"] == "failed"
    assert final["transcript"] is None


def test_upload_validations_and_404s(api_client, make_patient, faked_storage_and_stt):
    patient = make_patient("۵")

    bad_type = _upload(
        api_client,
        patient["id"],
        files={"file": ("note.pdf", b"%PDF", "application/pdf")},
    )
    assert bad_type.status_code == 422
    assert bad_type.json()["detail"] == INVALID_AUDIO_TYPE_DETAIL

    missing_patient = _upload(api_client, 999999)
    assert missing_patient.status_code == 404
    assert missing_patient.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


# --- list / get / patch / download ---


def test_list_newest_first_and_get_missing(api_client, make_patient, faked_storage_and_stt):
    patient = make_patient("۶")
    first = _upload(api_client, patient["id"]).json()
    second = _upload(api_client, patient["id"]).json()

    listing = api_client.get(VOICE_NOTES_NESTED_URL.format(patient_id=patient["id"]))
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [second["id"], first["id"]]

    missing = api_client.get(VOICE_NOTE_ITEM_URL.format(voice_note_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == VOICE_NOTE_NOT_FOUND_DETAIL


def test_patch_renames_only_title(api_client, make_patient, faked_storage_and_stt):
    patient = make_patient("۷")
    created = _upload(api_client, patient["id"]).json()

    patched = api_client.patch(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]),
        json={"title": "عنوان جدید"},
    )

    assert patched.status_code == 200
    assert patched.json()["title"] == "عنوان جدید"


def test_download_redirects_to_presigned(api_client, make_patient, faked_storage_and_stt):
    patient = make_patient("۸")
    created = _upload(api_client, patient["id"]).json()

    response = api_client.get(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]) + "/download",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"].startswith("http://minio.test/patients/")
    assert "/voice/" in response.headers["location"]


# --- review → clinical note workflow ---


def test_create_note_from_transcript_keeps_link_and_event(
    api_client, make_patient, faked_storage_and_stt, db_session
):
    patient = make_patient("۹")
    created = _upload(api_client, patient["id"]).json()

    note = api_client.post(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]) + "/note",
        json={"title": "خلاصه ویزیت صوتی", "content": "بیمار متفورمین را ادامه می‌دهد."},
    )

    assert note.status_code == 201, note.text
    body = note.json()
    assert body["source"] == "voice"
    assert body["voice_note_id"] == created["id"]
    assert body["patient_id"] == patient["id"]

    events = db_session.scalars(
        select(ClinicalEvent).where(
            ClinicalEvent.source_type == "clinical_note",
            ClinicalEvent.source_id == body["id"],
        )
    ).all()
    assert len(events) == 1


# --- delete ---


def test_delete_removes_audio_and_event_but_keeps_notes(
    api_client, make_patient, faked_storage_and_stt, db_session
):
    patient = make_patient("۱۰")
    created = _upload(api_client, patient["id"]).json()
    note = api_client.post(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]) + "/note",
        json={"title": "یادداشت", "content": "متن"},
    ).json()

    response = api_client.delete(VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]))

    assert response.status_code == 204
    assert faked_storage_and_stt["deleted"], "audio removed from storage"
    assert api_client.get(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"])
    ).status_code == 404

    events = db_session.scalars(
        select(ClinicalEvent).where(
            ClinicalEvent.source_type == "voice_note",
            ClinicalEvent.source_id == created["id"],
        )
    ).all()
    assert events == []

    # the derived clinical note survives, with the link cleared (SET NULL)
    surviving = db_session.scalars(
        select(ClinicalNote).where(ClinicalNote.id == note["id"])
    ).one()
    assert surviving.voice_note_id is None
    assert surviving.content == "متن"
