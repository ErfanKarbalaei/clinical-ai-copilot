"""PatientUserAccess — explicit patient↔user assignment (Task 18).

Doctors see only the patients explicitly assigned to them; admins bypass
this table. A logged-in user never gains access to every patient merely
by being authenticated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class PatientUserAccess(TimestampMixin, Base):
    """One explicit "this user may access this patient" grant."""

    __tablename__ = "patient_user_access"
    __table_args__ = (
        UniqueConstraint("patient_id", "user_id", name="uq_patient_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    patient: Mapped[Patient] = relationship(back_populates="user_access")
    user: Mapped[User] = relationship(back_populates="patient_access")

    def __repr__(self) -> str:
        return (
            f"<PatientUserAccess id={self.id} "
            f"patient_id={self.patient_id} user_id={self.user_id}>"
        )
