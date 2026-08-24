"""LabResult — a single selected structured lab value."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import ResultFlag

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.patient import Patient


class LabResult(TimestampMixin, Base):
    """One selected important lab value (NOT a full lab report).

    Full reports remain documents; only values worth structuring are stored
    here. ``value`` is text on purpose — it supports both numeric
    («۱۷۶», "168") and qualitative ("منفی", "Positive") results.
    """

    __tablename__ = "lab_results"
    __table_args__ = (
        Index("ix_lab_results_patient_date", "patient_id", "result_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE")
    )
    # Optional link to the document the value was extracted from; deleting
    # the document keeps the value (SET NULL).
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    test_name: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(String(100))
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range: Mapped[Optional[str]] = mapped_column(String(100))
    flag: Mapped[Optional[ResultFlag]] = mapped_column(
        SAEnum(ResultFlag, name="result_flag")
    )
    result_date: Mapped[Optional[date]] = mapped_column(Date)

    patient: Mapped[Patient] = relationship(back_populates="lab_results")
    document: Mapped[Optional[Document]] = relationship()

    def __repr__(self) -> str:
        return (
            f"<LabResult id={self.id} patient_id={self.patient_id} "
            f"test={self.test_name!r} value={self.value!r}>"
        )
