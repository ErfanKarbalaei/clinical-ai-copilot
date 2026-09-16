"""Voice-note AI-cleanup tests (STT + LLM provider mocked — no real calls)."""

import pytest

from app.api.v1.routes import voice_notes as voice_notes_routes
from app.api.v1.routes.voice_notes import AUDIO_TOO_LARGE_DETAIL
from app.models import VoiceNote
from app.services import ai, storage, voice_notes as voice_notes_service
from app.services.stt import TranscriptionError
from app.services.voice_note_cleanup import (
    _MAX_TRANSCRIPT_CHARS,
    TRANSCRIPT_CLEANUP_PROMPT,
    build_cleanup_message,
)

PATIENTS_URL = "/api/v1/patients"
VOICE_NOTES_NESTED_URL = "/api/v1/patients/{patient_id}/voice-notes"
VOICE_NOTE_ITEM_URL = "/api/v1/voice-notes/{voice_note_id}"

RAW_FA_TRANSCRIPT = (
    "بیمار از دیشب سردرد داره. فشار خون امروز صبح ۱۵ روی ۹ بوده. "
    "تهوع نداره. داروی لوزارتان مصرف می‌کنه."
)
CLEANED_NOTE = (
    "شکایت اصلی: سردرد از شب گذشته.\n"
    "سنجش‌ها و علائم حیاتی: فشار خون ۱۵۰/۹۰ (به گفتهٔ پزشک).\n"
    "علائم همراه: تهوع ندارد.\n"
    "داروهای ذکرشده: لوزارتان."
)
AUDIO_FILE = {"file": ("recording.webm", b"FAKE-WEBM-AUDIO", "audio/webm")}


class FakeProvider:
    """Records prompts; returns a canned response or raises."""

    def __init__(self, response: str = CLEANED_NOTE, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str, history=None) -> str:
        self.calls.append({"system": system, "user": user})
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture()
def pipeline(api_client, db_session, monkeypatch):
    """Fake storage + fake STT + the real pipeline on the isolated test session.

    Returns a controller so each test picks the AI-provider behaviour
    (success / failure / not configured) before uploading.
    """
    stored: dict[str, bytes] = {}

    def fake_upload(*, patient_id, file_name, content_type, data, folder="documents"):
        key = f"patients/{patient_id}/{folder}/fake-{len(stored) + 1}-{file_name}"
        stored[key] = data
        return key

    monkeypatch.setattr(storage, "upload_file", fake_upload)
    monkeypatch.setattr(storage, "delete_object", lambda key: None)
    monkeypatch.setattr(storage, "get_object_bytes", lambda key: stored[key])

    def fake_transcribe(*, data, file_name, mime_type, language="fa", diarize=False):
        if language != "fa":
            raise AssertionError("expected Persian (fa) transcription")
        return RAW_FA_TRANSCRIPT

    monkeypatch.setattr(
        "app.services.voice_notes.stt.transcribe_audio", fake_transcribe
    )
    monkeypatch.setattr(
        voice_notes_routes,
        "process_voice_note",
        lambda vn_id: voice_notes_service.process_voice_note(vn_id, db=db_session),
    )

    def with_provider(provider: FakeProvider) -> FakeProvider:
        monkeypatch.setattr(ai, "get_provider", lambda: provider)
        return provider

    def without_ai() -> None:
        def unavailable():
            raise ai.AIUnavailableError("AI_API_KEY is not configured")

        monkeypatch.setattr(ai, "get_provider", unavailable)

    return {"with_provider": with_provider, "without_ai": without_ai}


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"پاک‌سازی {suffix}"},
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


def _fetch(api_client, voice_note_id: int) -> dict:
    response = api_client.get(VOICE_NOTE_ITEM_URL.format(voice_note_id=voice_note_id))
    assert response.status_code == 200, response.text
    return response.json()


# --- prompt safety (Gemini must not invent medical information) ---


def test_cleanup_prompt_is_safety_scoped():
    assert "FORMATTING AND CLARIFICATION ONLY" in TRANSCRIPT_CLEANUP_PROMPT
    assert "ONLY information present in the transcript" in TRANSCRIPT_CLEANUP_PROMPT
    assert "Do NOT add diagnoses" in TRANSCRIPT_CLEANUP_PROMPT
    assert "Do NOT add medications" in TRANSCRIPT_CLEANUP_PROMPT
    assert "Do NOT add symptoms" in TRANSCRIPT_CLEANUP_PROMPT
    assert "Do NOT add measurements" in TRANSCRIPT_CLEANUP_PROMPT
    assert "never guess" in TRANSCRIPT_CLEANUP_PROMPT
    assert "Preserve uncertainty" in TRANSCRIPT_CLEANUP_PROMPT


def test_build_cleanup_message_includes_and_caps_transcript(
    api_client, db_session, make_patient
):
    patient = make_patient("۱")
    voice_note = VoiceNote(
        patient_id=patient["id"],
        title="ویزیت صبح",
        audio_storage_key="test-cleanup-cap",
        transcript="سردرد " + "ط" * (_MAX_TRANSCRIPT_CHARS + 100),
    )
    db_session.add(voice_note)
    db_session.commit()

    message = build_cleanup_message(voice_note)

    assert "سردرد" in message
    assert "ویزیت صبح" in message
    assert "بریده شد" in message  # truncation marker
    assert len(message) < _MAX_TRANSCRIPT_CHARS + 200


# --- full pipeline: transcription + optional AI cleanup ---


def test_upload_transcribes_then_cleans(api_client, make_patient, pipeline):
    provider = pipeline["with_provider"](FakeProvider())
    patient = make_patient("۲")

    created = _upload(api_client, patient["id"]).json()
    final = _fetch(api_client, created["id"])

    assert final["transcription_status"] == "completed"
    assert final["transcript"] == RAW_FA_TRANSCRIPT  # raw preserved as-is
    assert final["cleaned_note"] == CLEANED_NOTE
    assert final["cleanup_status"] == "completed"
    assert final["processed_at"] is not None
    # the cleanup prompt is grounded in the actual transcript
    assert len(provider.calls) == 1
    assert RAW_FA_TRANSCRIPT in provider.calls[0]["user"]
    assert "Do NOT add diagnoses" in provider.calls[0]["system"]


def test_cleanup_failure_preserves_raw_transcript(api_client, make_patient, pipeline):
    provider = pipeline["with_provider"](
        FakeProvider(error=ai.AIError("provider down"))
    )
    patient = make_patient("۳")

    created = _upload(api_client, patient["id"]).json()
    final = _fetch(api_client, created["id"])

    # transcription succeeded — the Gemini failure must never mask that
    assert final["transcription_status"] == "completed"
    assert final["transcript"] == RAW_FA_TRANSCRIPT
    assert final["cleaned_note"] is None
    assert final["cleanup_status"] == "failed"
    assert provider.calls  # cleanup was attempted


def test_cleanup_skipped_when_ai_unconfigured(api_client, make_patient, pipeline):
    provider = pipeline["with_provider"](FakeProvider())
    pipeline["without_ai"]()
    patient = make_patient("۴")

    created = _upload(api_client, patient["id"]).json()
    final = _fetch(api_client, created["id"])

    assert final["transcription_status"] == "completed"
    assert final["transcript"] == RAW_FA_TRANSCRIPT
    assert final["cleaned_note"] is None
    assert final["cleanup_status"] == "pending"  # optional step, not attempted
    assert provider.calls == []


def test_stt_failure_stores_error_and_processed_at(
    api_client, make_patient, pipeline, monkeypatch
):
    provider = pipeline["with_provider"](FakeProvider())

    def broken_transcribe(**kwargs):
        raise TranscriptionError("job error: audio too short")

    monkeypatch.setattr(
        "app.services.voice_notes.stt.transcribe_audio", broken_transcribe
    )
    patient = make_patient("۵")

    created = _upload(api_client, patient["id"]).json()
    final = _fetch(api_client, created["id"])

    assert final["transcription_status"] == "failed"
    assert final["transcript"] is None
    assert "audio too short" in final["error_message"]
    assert final["processed_at"] is not None
    assert final["cleaned_note"] is None
    assert final["cleanup_status"] == "pending"
    assert provider.calls == []  # nothing to clean without a transcript


def test_retranscribe_resets_cleanup(api_client, make_patient, pipeline):
    pipeline["with_provider"](FakeProvider())
    patient = make_patient("۶")

    created = _upload(api_client, patient["id"]).json()
    assert _fetch(api_client, created["id"])["cleaned_note"] == CLEANED_NOTE

    # retry with AI unavailable → fresh transcript, stale cleanup discarded
    pipeline["without_ai"]()
    retried = api_client.post(
        VOICE_NOTE_ITEM_URL.format(voice_note_id=created["id"]) + "/transcribe"
    )
    assert retried.status_code == 202

    final = _fetch(api_client, created["id"])
    assert final["transcription_status"] == "completed"
    assert final["transcript"] == RAW_FA_TRANSCRIPT
    assert final["cleaned_note"] is None
    assert final["cleanup_status"] == "pending"


# --- patient context + timeline integration (Tasks 9 architecture) ---


def test_context_and_timeline_carry_voice_note(api_client, make_patient, pipeline):
    pipeline["with_provider"](FakeProvider())
    patient = make_patient("۷")
    created = _upload(api_client, patient["id"], data={"title": "ویزیت صبح"}).json()

    context = api_client.get(f"{PATIENTS_URL}/{patient['id']}/context").json()
    assert len(context["voice_notes"]) == 1
    carried = context["voice_notes"][0]
    assert carried["id"] == created["id"]
    assert carried["transcript"] == RAW_FA_TRANSCRIPT
    assert carried["cleaned_note"] == CLEANED_NOTE

    timeline = api_client.get(f"{PATIENTS_URL}/{patient['id']}/timeline").json()
    voice_events = [
        item for item in timeline["items"] if item["source_type"] == "voice_note"
    ]
    assert len(voice_events) == 1
    assert voice_events[0]["event_type"] == "voice_note_recorded"
    assert voice_events[0]["source_id"] == created["id"]


# --- upload validation: oversized audio ---


def test_oversized_audio_rejected(api_client, make_patient, pipeline, monkeypatch):
    patient = make_patient("۸")
    monkeypatch.setattr(voice_notes_routes, "MAX_AUDIO_SIZE_BYTES", 16)

    oversized = {"file": ("big.webm", b"x" * 64, "audio/webm")}
    response = _upload(api_client, patient["id"], files=oversized)

    assert response.status_code == 422
    assert response.json()["detail"] == AUDIO_TOO_LARGE_DETAIL
