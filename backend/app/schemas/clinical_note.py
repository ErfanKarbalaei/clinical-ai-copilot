"""Pydantic schemas for clinical notes (response only — used in patient overview)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NoteSource


class ClinicalNoteResponse(BaseModel):
    """A clinical note (content included — overview preview)."""

    id: int
    patient_id: int
    voice_note_id: int | None = None
    title: str
    content: str
    source: NoteSource
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
