"""Optional AI cleanup/formatting of a voice-note transcript.

Reuses the existing provider-agnostic AI layer (Tasks 10 / 10.5 / 12). The
cleaned note is DERIVED data: it is stored on the voice-note row for
convenience but never replaces the original audio or the raw transcript —
both remain the source of truth.

This is a documentation assistant, NOT a voice doctor: the model may only
FORMAT and CLARIFY what was actually said. The prompt forbids inventing
diagnoses, medications, symptoms, or measurements, and requires preserving
uncertainty. A cleanup failure never touches the raw transcript — it only
marks ``cleanup_status=failed``.
"""

import logging

from sqlalchemy.orm import Session

from app.models import VoiceNote
from app.models.enums import AnalysisStatus
from app.services import ai

logger = logging.getLogger(__name__)

# Safety-scoped prompt: formatting only — never clinical reasoning.
TRANSCRIPT_CLEANUP_PROMPT = """You format a Persian physician's voice dictation into a clean clinical note.
You receive the raw speech-to-text transcript of one voice note.

This task is FORMATTING AND CLARIFICATION ONLY — never clinical reasoning.

Rules:
- Use ONLY information present in the transcript. Do not add information.
- Do NOT add diagnoses.
- Do NOT add medications that were not mentioned.
- Do NOT add symptoms that were not mentioned.
- Do NOT add measurements.
- Do NOT infer or fill in missing information; never guess.
- Preserve uncertainty: if something is unclear or ambiguous in the
  transcript, keep it unclear rather than guessing.
- Organize into short labeled sections ONLY when the transcript contains
  them, e.g. «شکایت اصلی», «علائم همراه», «سنجش‌ها و علائم حیاتی»,
  «داروهای ذکرشده». Omit any section the transcript does not support.
- Keep numbers, units, and drug names exactly as spoken (Latin form where
  the transcript uses it).
- If the transcript has speaker tags (S1:/S2:), keep the turns attributed.
- Respond in Persian. Be concise: at most ~200 words.
- Output only the note text — no preamble, no explanations.
- Decision support only; the physician makes the final decision.
"""

# Cap on the transcript sent to the provider (defense against huge files).
_MAX_TRANSCRIPT_CHARS = 20_000


def build_cleanup_message(voice_note: VoiceNote) -> str:
    """Serialize voice-note metadata + capped transcript for the provider."""
    transcript = (voice_note.transcript or "").strip()
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:_MAX_TRANSCRIPT_CHARS] + "\n… [متن بریده شد]"
    return (
        f"Voice note title: {voice_note.title or 'بدون عنوان'}\n"
        f"Conversation type: {voice_note.conversation_type.value}\n"
        f"Raw transcript:\n{transcript or '(خالی)'}"
    )


def attempt_cleanup(db: Session, voice_note: VoiceNote) -> None:
    """Best-effort AI cleanup after a successful transcription — never raises.

    Runs only when an AI provider is configured (``AIUnavailableError`` →
    silently skipped, cleanup stays pending). Any failure — provider outage,
    bad key, unexpected error — is swallowed: ``cleaned_note`` stays/gets
    null, ``cleanup_status`` becomes ``failed``, and the raw transcript and
    the completed transcription status are left fully intact. The caller
    must have already committed the transcription result.
    """
    transcript = (voice_note.transcript or "").strip()
    if not transcript:
        return  # nothing transcribed — nothing to clean

    try:
        provider = ai.get_provider()
    except ai.AIUnavailableError:
        return  # optional feature — not configured, stays pending

    try:
        cleaned = provider.complete(
            system=TRANSCRIPT_CLEANUP_PROMPT,
            user=build_cleanup_message(voice_note),
        ).strip()
        voice_note.cleaned_note = cleaned or None
        voice_note.cleanup_status = (
            AnalysisStatus.completed if cleaned else AnalysisStatus.failed
        )
        db.commit()
        logger.info(
            "transcript cleanup ok (voice_note=%s, %d chars)",
            voice_note.id, len(cleaned),
        )
    except Exception as error:  # noqa: BLE001 — cleanup must never fail the pipeline
        voice_note.cleaned_note = None
        voice_note.cleanup_status = AnalysisStatus.failed
        try:
            db.commit()
        except Exception:  # noqa: BLE001 — DB hiccups must not propagate either
            db.rollback()
        logger.warning(
            "transcript cleanup failed (voice_note=%s): %s: %s",
            voice_note.id, type(error).__name__, error,
        )
