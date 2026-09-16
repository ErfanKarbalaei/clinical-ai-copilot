"""Pydantic schemas for the voice-note API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AnalysisStatus,
    ConversationType,
    TranscriptionStatus,
)


class VoiceNoteUpdate(BaseModel):
    """Payload for partially updating a voice note (title only).

    The raw transcript is never edited in place — corrections become a
    ClinicalNote via POST /voice-notes/{id}/note.
    """

    title: str | None = Field(default=None, min_length=1, max_length=300)


class CreateNoteFromTranscript(BaseModel):
    """Doctor-reviewed version of a transcript, saved as a clinical note."""

    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class VoiceNoteResponse(BaseModel):
    """Voice-note representation returned by the API."""

    id: int
    patient_id: int
    title: str | None
    conversation_type: ConversationType
    duration_seconds: int | None
    language: str
    transcription_status: TranscriptionStatus
    transcript: str | None
    cleanup_status: AnalysisStatus
    cleaned_note: str | None
    error_message: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
