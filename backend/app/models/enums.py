"""Enumerations used by the ORM models.

Design notes:
- Every member name equals its stored string value, so SQLAlchemy's default
  behaviour (persisting enum member *names*) stores the readable value.
- Each class becomes a native PostgreSQL enum type (explicit ``name=`` is
  passed where each enum is used in a column).
"""

from enum import StrEnum


class Gender(StrEnum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class ConditionStatus(StrEnum):
    active = "active"
    resolved = "resolved"


class MedicationStatus(StrEnum):
    active = "active"
    stopped = "stopped"
    completed = "completed"


class AllergySeverity(StrEnum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    unknown = "unknown"


class DocumentType(StrEnum):
    lab_report = "lab_report"
    imaging_report = "imaging_report"
    discharge_summary = "discharge_summary"
    medical_note = "medical_note"
    other = "other"


class ExtractionStatus(StrEnum):
    """Lifecycle of text extraction for an uploaded document."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AnalysisStatus(StrEnum):
    """Lifecycle of the optional AI analysis of a document's extracted text."""

    pending = "pending"
    completed = "completed"
    failed = "failed"


class TranscriptionStatus(StrEnum):
    """Lifecycle of speech-to-text processing for a voice note."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class NoteSource(StrEnum):
    """Origin of a clinical note (traceability of derived data)."""

    manual = "manual"
    voice = "voice"
    ai_assisted = "ai_assisted"


class ConversationType(StrEnum):
    """The two supported voice-documentation workflows."""

    physician_note = "physician_note"
    doctor_patient = "doctor_patient"


class ChatRole(StrEnum):
    """Author of one message inside a persisted clinical conversation."""

    user = "user"
    assistant = "assistant"


class ResultFlag(StrEnum):
    normal = "normal"
    abnormal = "abnormal"
    critical = "critical"


class UserRole(StrEnum):
    """MVP application roles (no complex RBAC)."""

    doctor = "doctor"
    admin = "admin"
