"""Medication catalog and per-patient medication records."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import MedicationStatus

if TYPE_CHECKING:
    from app.models.patient import Patient


class Medication(TimestampMixin, Base):
    """Catalog entry for a medication (shared across patients).

    Kept minimal on purpose (name + generic name); richer drug data
    (RxNorm codes, interactions, ...) is intentionally deferred until the
    prescription-safety subsystem is designed.
    """

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(200))

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name!r}>"


class PatientMedication(TimestampMixin, Base):
    """A medication taken by a patient, with dosage/frequency/period."""

    __tablename__ = "patient_medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    # No ON DELETE action: catalog rows cannot be deleted while referenced.
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medications.id"), index=True
    )
    dosage: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. "500 mg"
    frequency: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. «دو بار در روز»
    status: Mapped[MedicationStatus] = mapped_column(
        SAEnum(MedicationStatus, name="medication_status"),
        default=MedicationStatus.active,
        server_default="active",
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient: Mapped[Patient] = relationship(back_populates="patient_medications")
    medication: Mapped[Medication] = relationship()

    def __repr__(self) -> str:
        return (
            f"<PatientMedication id={self.id} patient_id={self.patient_id} "
            f"medication_id={self.medication_id} status={self.status}>"
        )
