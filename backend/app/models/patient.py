"""Patient — the root entity of all clinical data."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import Gender

if TYPE_CHECKING:
    from app.models.allergy import Allergy
    from app.models.clinical_event import ClinicalEvent
    from app.models.clinical_note import ClinicalNote
    from app.models.condition import Condition
    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.lab_result import LabResult
    from app.models.medication import PatientMedication
    from app.models.patient_user_access import PatientUserAccess
    from app.models.voice_note import VoiceNote


class Patient(TimestampMixin, Base):
    """Basic patient profile.

    Clinical details (conditions, medications, allergies, documents, ...)
    live in the linked entities — this table holds only identifying data.
    """

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    # Iranian national identity code (کد ملی) — exactly 10 digits, unique.
    national_code: Mapped[Optional[str]] = mapped_column(String(10), unique=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Gender] = mapped_column(
        SAEnum(Gender, name="gender"),
        default=Gender.unknown,
        server_default="unknown",
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)

    # --- related clinical data (all rows are removed with the patient) ---
    conditions: Mapped[list[Condition]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    allergies: Mapped[list[Allergy]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    patient_medications: Mapped[list[PatientMedication]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    voice_notes: Mapped[list[VoiceNote]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    clinical_notes: Mapped[list[ClinicalNote]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    lab_results: Mapped[list[LabResult]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    clinical_events: Mapped[list[ClinicalEvent]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
    user_access: Mapped[list[PatientUserAccess]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} {self.first_name} {self.last_name}>"
