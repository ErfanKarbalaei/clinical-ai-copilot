"""Speech-to-Text — provider-agnostic layer with a Speechmatics implementation.

Ready-to-use cloud model — no training, no local inference. Any provider
implements the tiny :class:`SpeechToTextProvider` interface and is selected
by configuration (``STT_PROVIDER``); the voice-note workflow only ever
calls :func:`transcribe_audio` and never knows which backend ran.

Speechmatics batch API flow:

1. POST /jobs        — multipart: job config JSON + the original audio file
2. poll GET /jobs/{id} until the job is ``done`` (or ``error``/timeout)
3. GET /jobs/{id}/transcript?format=json-v2 — word/segment-level result,
   including speaker tags when diarization was requested

The transcript we KEEP is the raw model output (formatted for readability,
never edited in place) — reviewed text becomes a ClinicalNote instead.
"""

import json
import logging
import time
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Transcription could not be performed."""


class SttUnavailableError(TranscriptionError):
    """No API key configured — STT cannot run."""


_http_client: httpx.Client | None = None


def _client() -> httpx.Client:
    """Module-level HTTP client (injectable in tests via this attribute)."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=httpx.Timeout(60.0))
    return _http_client


class SpeechToTextProvider(Protocol):
    """Minimal STT interface (swap providers by implementing this)."""

    def transcribe(
        self,
        *,
        data: bytes,
        file_name: str,
        mime_type: str,
        language: str = "fa",
        diarize: bool = False,
    ) -> str: ...


def format_transcript_json(payload: dict) -> str:
    """Assemble a json-v2 transcript into readable text.

    Keeps speaker turns on separate lines when diarization tags exist:
    ``S1: سلام\nS2: سلام، حال شما چطور است؟``
    """
    parts: list[str] = []
    current_speaker: str | None = None
    for result in payload.get("results", []):
        alternatives = result.get("alternatives") or []
        if not alternatives:
            continue
        alternative = alternatives[0]
        content = (alternative.get("content") or "").strip()
        if not content:
            continue
        speaker = alternative.get("speaker")
        if speaker and speaker != current_speaker:
            parts.append(f"\n{speaker}: {content}")
            current_speaker = speaker
        else:
            parts.append(content)
    return " ".join(parts).replace(" \n", "\n").strip()


class SpeechmaticsProvider:
    """Speechmatics batch API (``fa``-capable, ``enhanced`` operating point)."""

    def __init__(self, *, api_key: str):
        settings = get_settings()
        self.api_key = api_key
        self.base_url = settings.SPEECHMATICS_BASE_URL
        self.poll_interval = settings.STT_POLL_INTERVAL_SECONDS
        self.timeout = settings.STT_TIMEOUT_SECONDS

    def transcribe(
        self,
        *,
        data: bytes,
        file_name: str,
        mime_type: str,
        language: str = "fa",
        diarize: bool = False,
    ) -> str:
        """Submit audio, wait for the job, return the raw transcript text.

        ``diarize=True`` is used for doctor–patient conversations;
        single-speaker physician notes skip it (cheaper and faster).
        """
        job_config = {
            "type": "transcription",
            "transcription_config": {
                "language": language,
                "operating_point": "enhanced",
            },
        }
        if diarize:
            job_config["transcription_config"]["diarization"] = "max"

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # 1) submit the job
        submit = _client().post(
            f"{self.base_url}/jobs",
            headers=headers,
            files={"data_file": (file_name, data, mime_type)},
            data={"config": json.dumps(job_config)},
        )
        if submit.status_code in (401, 403):
            raise TranscriptionError("Speechmatics rejected the API key")
        if submit.status_code != 201:
            raise TranscriptionError(
                f"job submission failed ({submit.status_code}): {submit.text[:200]}"
            )
        job_id = submit.json()["id"]

        # 2) poll until done / error / timeout
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            time.sleep(self.poll_interval)
            status = _client().get(
                f"{self.base_url}/jobs/{job_id}", headers=headers
            )
            if status.status_code != 200:
                raise TranscriptionError(
                    f"job status failed ({status.status_code})"
                )
            job = status.json().get("job", {})
            state = job.get("status")
            if state == "done":
                break
            if state in ("error", "rejected", "cant_run"):
                raise TranscriptionError(
                    f"job {state}: {job.get('failure_message', 'no details')}"
                )
        else:
            raise TranscriptionError(
                f"job {job_id} did not finish within {self.timeout}s"
            )

        # 3) fetch the transcript (json-v2 keeps speaker tags)
        transcript = _client().get(
            f"{self.base_url}/jobs/{job_id}/transcript",
            headers=headers,
            params={"format": "json-v2"},
        )
        if transcript.status_code != 200:
            raise TranscriptionError(
                f"transcript fetch failed ({transcript.status_code})"
            )
        text = format_transcript_json(transcript.json())
        logger.info(
            "Speechmatics job %s done (%d chars, diarize=%s)",
            job_id, len(text), diarize,
        )
        return text


def get_stt_provider() -> SpeechToTextProvider:
    """Build the configured provider (``STT_PROVIDER``; key from STT_API_KEY
    with SPEECHMATICS_API_KEY as the legacy fallback)."""
    settings = get_settings()
    api_key = settings.STT_API_KEY or settings.SPEECHMATICS_API_KEY
    if not api_key:
        raise SttUnavailableError(
            "STT_API_KEY (or SPEECHMATICS_API_KEY) is not configured"
        )
    if settings.STT_PROVIDER != "speechmatics":
        raise TranscriptionError(
            f"unknown STT_PROVIDER: {settings.STT_PROVIDER!r}"
        )
    return SpeechmaticsProvider(api_key=api_key)


def transcribe_audio(
    *,
    data: bytes,
    file_name: str,
    mime_type: str,
    language: str = "fa",
    diarize: bool = False,
) -> str:
    """Transcribe audio via the configured provider (provider-agnostic facade)."""
    return get_stt_provider().transcribe(
        data=data,
        file_name=file_name,
        mime_type=mime_type,
        language=language,
        diarize=diarize,
    )
