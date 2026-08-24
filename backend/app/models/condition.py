"""Condition — a disease/condition recorded for a patient."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import ConditionStatus

if TYPE_CHECKING:
    from app.models.patient import Patient


class Condition(TimestampMixin, Base):
    """A patient-scoped clinical condition (e.g. «دیابت نوع ۲»).

    Stored per patient rather than as a catalog link — conditions are
    entered as free clinical text, optionally with onset/resolution dates.
    """

    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[ConditionStatus] = mapped_column(
        SAEnum(ConditionStatus, name="condition_status"),
        default=ConditionStatus.active,
        server_default="active",
    )
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    resolved_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient: Mapped[Patient] = relationship(back_populates="conditions")

    def __repr__(self) -> str:
        return f"<Condition id={self.id} patient_id={self.patient_id} name={self.name!r}>"
