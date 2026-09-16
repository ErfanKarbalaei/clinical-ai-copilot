"""Voice-note processing orchestration: transcription status lifecycle.

Mirrors the documents pipeline: runs as a FastAPI background task after
upload, opens its own session, never crashes on failure. The raw transcript
is preserved as produced by speech-to-text — reviewed/edited text becomes a
ClinicalNote instead (separate, explicit doctor action).

After a successful transcription, an OPTIONAL AI cleanup pass
(voice_note_cleanup.attempt_cleanup) formats the transcript into a concise
clinical note. Cleanup is best-effort: it can never turn a completed
transcription into a failure and never touches the raw transcript.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import VoiceNote
from app.models.enums import (
    AnalysisStatus,
    ConversationType,
    TranscriptionStatus,
)
from app.services import storage, stt
from app.services.voice_note_cleanup import attempt_cleanup

logger = logging.getLogger(__name__)


def process_voice_note(voice_note_id: int, db: Session | None = None) -> None:
    """Transcribe one voice note and persist the raw transcript.

    Status lifecycle: pending → processing → completed | failed.
    """
    if db is None:
        with SessionLocal() as session:
            _process(session, voice_note_id)
        return
    _process(db, voice_note_id)


def _process(db: Session, voice_note_id: int) -> None:
    voice_note = db.get(VoiceNote, voice_note_id)
    if voice_note is None:
        logger.warning("process_voice_note: voice note %s not found", voice_note_id)
        return

    try:
        voice_note.transcription_status = TranscriptionStatus.processing
        # fresh run: a previous derived cleanup no longer matches a new transcript
        voice_note.cleaned_note = None
        voice_note.cleanup_status = AnalysisStatus.pending
        voice_note.error_message = None
        db.commit()

        data = storage.get_object_bytes(voice_note.audio_storage_key)
        transcript = stt.transcribe_audio(
            data=data,
            file_name=voice_note.audio_storage_key.rsplit("/", 1)[-1],
            mime_type=_audio_mime(voice_note.audio_storage_key),
            language=voice_note.language or "fa",
            diarize=voice_note.conversation_type
            == ConversationType.doctor_patient,
        )
        voice_note.transcript = transcript.strip() or None
        voice_note.transcription_status = TranscriptionStatus.completed
        voice_note.processed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "transcription ok (voice_note=%s, %d chars)",
            voice_note_id, len(transcript),
        )

        # optional AI cleanup — best effort, transcription already committed
        attempt_cleanup(db, voice_note)
    except SQLAlchemyError as error:
        db.rollback()
        logger.warning(
            "transcription aborted — voice note %s changed/deleted concurrently: %s",
            voice_note_id, error,
        )
    except Exception as error:  # noqa: BLE001 — any failure → failed status
        voice_note.transcript = None
        voice_note.transcription_status = TranscriptionStatus.failed
        voice_note.error_message = str(error)[:1000] or type(error).__name__
        voice_note.processed_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        logger.warning("transcription failed (voice_note=%s): %s", voice_note_id, error)


_MIME_BY_EXTENSION = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
}


def _audio_mime(storage_key: str) -> str:
    """Best-effort mime from the stored key extension (Speechmatics hint)."""
    dot = storage_key.rfind(".")
    if dot != -1:
        mime = _MIME_BY_EXTENSION.get(storage_key[dot:].lower())
        if mime:
            return mime
    return "audio/webm"
