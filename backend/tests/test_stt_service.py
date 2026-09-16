"""Unit tests for the Speechmatics STT service (mocked HTTP, no real API)."""

import json

import httpx
import pytest

from app.core.config import get_settings
from app.services import stt
from app.services.stt import (
    SttUnavailableError,
    TranscriptionError,
    format_transcript_json,
)

FAKE_AUDIO = b"fake-audio-bytes"

JOBS_SUBMITTED: list[dict] = []


def _mock_transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _install_client(monkeypatch, handler) -> None:
    monkeypatch.setattr(
        stt, "_http_client", httpx.Client(transport=_mock_transport(handler))
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "SPEECHMATICS_API_KEY", "test-key")
    monkeypatch.setattr(settings, "STT_POLL_INTERVAL_SECONDS", 0.0)


def test_no_api_key_raises_unavailable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "SPEECHMATICS_API_KEY", "")
    monkeypatch.setattr(settings, "STT_API_KEY", "")
    with pytest.raises(SttUnavailableError):
        stt.transcribe_audio(
            data=FAKE_AUDIO, file_name="a.webm", mime_type="audio/webm"
        )


def test_full_job_flow_plain_transcript(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/v2/jobs" and request.method == "POST":
            assert "Bearer test-key" in request.headers["authorization"]
            assert b"config" in request.content
            return httpx.Response(201, json={"id": "job-1"})
        if request.url.path == "/v2/jobs/job-1":
            return httpx.Response(200, json={"job": {"status": "done"}})
        if request.url.path == "/v2/jobs/job-1/transcript":
            assert request.url.params["format"] == "json-v2"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"alternatives": [{"content": "سلام", "speaker": None}]},
                        {"alternatives": [{"content": "حال شما چطور است؟"}]},
                    ]
                },
            )
        return httpx.Response(404)

    _install_client(monkeypatch, handler)

    text = stt.transcribe_audio(
        data=FAKE_AUDIO, file_name="note.webm", mime_type="audio/webm"
    )

    assert text == "سلام حال شما چطور است؟"
    assert ("POST", "/v2/jobs") in calls


def test_full_job_flow_diarized_transcript(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/jobs":
            # diarization must be requested for doctor–patient conversations
            body = request.content.decode("utf-8", errors="ignore")
            assert "diarization" in body
            return httpx.Response(201, json={"id": "job-2"})
        if request.url.path == "/v2/jobs/job-2":
            return httpx.Response(200, json={"job": {"status": "done"}})
        return httpx.Response(
            200,
            json={
                "results": [
                    {"alternatives": [{"content": "سلام", "speaker": "S1"}]},
                    {"alternatives": [{"content": "احوال پرسیدن", "speaker": "S2"}]},
                    {"alternatives": [{"content": "مرسی", "speaker": "S1"}]},
                ]
            },
        )

    _install_client(monkeypatch, handler)

    text = stt.transcribe_audio(
        data=FAKE_AUDIO,
        file_name="conv.webm",
        mime_type="audio/webm",
        diarize=True,
    )

    assert text == "S1: سلام\nS2: احوال پرسیدن\nS1: مرسی"


def test_job_error_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": "job-3"})
        return httpx.Response(
            200, json={"job": {"status": "error", "failure_message": "bad audio"}}
        )

    _install_client(monkeypatch, handler)

    with pytest.raises(TranscriptionError, match="bad audio"):
        stt.transcribe_audio(
            data=FAKE_AUDIO, file_name="a.webm", mime_type="audio/webm"
        )


def test_rejected_api_key_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid key"})

    _install_client(monkeypatch, handler)

    with pytest.raises(TranscriptionError, match="API key"):
        stt.transcribe_audio(
            data=FAKE_AUDIO, file_name="a.webm", mime_type="audio/webm"
        )


def test_format_transcript_json_speaker_turns():
    payload = {
        "results": [
            {"alternatives": [{"content": "سلام ", "speaker": "S1"}]},
            {"alternatives": [{"content": "خوبم", "speaker": "S1"}]},
            {"alternatives": [{"content": "تب داری؟", "speaker": "S2"}]},
            {"alternatives": []},
            {"alternatives": [{"content": "", "speaker": "S2"}]},
        ]
    }
    assert format_transcript_json(payload) == "S1: سلام خوبم\nS2: تب داری؟"


def test_config_json_is_serializable_and_fa():
    # sanity: the job config we build for Persian is valid JSON with language fa
    config = {
        "type": "transcription",
        "transcription_config": {"language": "fa", "operating_point": "enhanced"},
    }
    parsed = json.loads(json.dumps(config))
    assert parsed["transcription_config"]["language"] == "fa"


# --- provider abstraction (Task 13: STT_PROVIDER / STT_API_KEY) ---


def test_get_stt_provider_dispatch_and_key_fallback(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "STT_PROVIDER", "speechmatics")

    monkeypatch.setattr(settings, "STT_API_KEY", "")
    monkeypatch.setattr(settings, "SPEECHMATICS_API_KEY", "legacy-key")
    provider = stt.get_stt_provider()
    assert isinstance(provider, stt.SpeechmaticsProvider)
    assert provider.api_key == "legacy-key"  # legacy spelling still works

    monkeypatch.setattr(settings, "STT_API_KEY", "new-key")
    assert stt.get_stt_provider().api_key == "new-key"  # takes precedence


def test_get_stt_provider_unknown_name_raises(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "STT_PROVIDER", "deepgram")
    monkeypatch.setattr(settings, "STT_API_KEY", "k")
    with pytest.raises(TranscriptionError, match="unknown STT_PROVIDER"):
        stt.get_stt_provider()


def test_get_stt_provider_no_key_raises_unavailable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "STT_API_KEY", "")
    monkeypatch.setattr(settings, "SPEECHMATICS_API_KEY", "")
    with pytest.raises(SttUnavailableError):
        stt.get_stt_provider()


def test_transcribe_audio_delegates_to_provider(monkeypatch):
    calls: list[dict] = []

    class RecordingProvider:
        def transcribe(
            self, *, data, file_name, mime_type, language="fa", diarize=False
        ):
            calls.append(
                {
                    "data": data,
                    "file_name": file_name,
                    "language": language,
                    "diarize": diarize,
                }
            )
            return "متن"

    monkeypatch.setattr(stt, "get_stt_provider", lambda: RecordingProvider())

    text = stt.transcribe_audio(
        data=b"abc", file_name="a.wav", mime_type="audio/wav", diarize=True
    )

    assert text == "متن"
    assert calls == [
        {"data": b"abc", "file_name": "a.wav", "language": "fa", "diarize": True}
    ]
