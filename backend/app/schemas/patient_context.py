"""Pydantic schemas for the patient context and clinical timeline APIs."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.allergy import AllergyResponse
from app.schemas.clinical_note import ClinicalNoteResponse
from app.schemas.condition import ConditionResponse
from app.schemas.document import DocumentResponse
from app.schemas.lab_result import LabResultResponse
from app.schemas.medication import PatientMedicationResponse
from app.schemas.patient import PatientResponse
from app.schemas.voice_note import VoiceNoteResponse


class PatientContextResponse(BaseModel):
    """Complete structured patient context — pure database data, no AI.

    Everything the future AI clinical copilot needs as input: demographics,
    conditions, medications (with history), allergies, lab values, documents
    (incl. extracted text), voice notes (incl. raw transcripts) and clinical
    notes — all in one response, sourced live from the existing tables.
    """

    patient: PatientResponse
    conditions: list[ConditionResponse] = Field(description="فعال‌ها اول")
    medications: list[PatientMedicationResponse] = Field(
        description="همهٔ داروها با وضعیت (active/stopped/completed)"
    )
    allergies: list[AllergyResponse] = Field(description="شدیدترها اول")
    lab_results: list[LabResultResponse] = Field(description="جدیدترین اول")
    documents: list[DocumentResponse] = Field(description="جدیدترین اول")
    voice_notes: list[VoiceNoteResponse] = Field(description="جدیدترین اول")
    clinical_notes: list[ClinicalNoteResponse] = Field(description="جدیدترین اول")
    generated_at: datetime


class TimelineItem(BaseModel):
    """One entry of the unified clinical timeline (newest first)."""

    event_type: str
    date: datetime
    title: str
    description: str | None = None
    source_type: str
    source_id: int


class PatientTimelineResponse(BaseModel):
    items: list[TimelineItem]
    total: int
