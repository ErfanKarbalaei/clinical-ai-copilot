"""ClinicalEvent — a patient timeline event."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.patient import Patient


class ClinicalEvent(TimestampMixin, Base):
    """A timeline event for a patient (condition onset, lab result,
    medication change, document upload, visit, ...).

    ``source_type`` / ``source_id`` optionally point back to the row this
    event was derived from (e.g. source_type="lab_result", source_id=12) so
    timeline items stay traceable to their original record. This is a
    polymorphic reference without a database-level FK by design — the event
    type set is open and events may also be entered manually.
    """

    __tablename__ = "clinical_events"
    __table_args__ = (
        Index("ix_clinical_events_patient_date", "patient_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE")
    )
    # Open set, e.g. condition_onset, medication_started, lab_result,
    # document_uploaded, voice_note_recorded, note_created, visit.
    event_type: Mapped[str] = mapped_column(String(50))
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[Optional[str]] = mapped_column(String(30))
    source_id: Mapped[Optional[int]] = mapped_column(Integer)

    patient: Mapped[Patient] = relationship(back_populates="clinical_events")

    def __repr__(self) -> str:
        return (
            f"<ClinicalEvent id={self.id} patient_id={self.patient_id} "
            f"type={self.event_type!r} date={self.event_date}>"
        )
