"""Allergy — a recorded allergy for a patient."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import AllergySeverity

if TYPE_CHECKING:
    from app.models.patient import Patient


class Allergy(TimestampMixin, Base):
    """An allergy/intolerance recorded for a patient (drug, food, ...)."""

    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    allergen: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[Optional[str]] = mapped_column(String(300))
    severity: Mapped[AllergySeverity] = mapped_column(
        SAEnum(AllergySeverity, name="allergy_severity"),
        default=AllergySeverity.unknown,
        server_default="unknown",
    )

    patient: Mapped[Patient] = relationship(back_populates="allergies")

    def __repr__(self) -> str:
        return f"<Allergy id={self.id} patient_id={self.patient_id} allergen={self.allergen!r}>"
