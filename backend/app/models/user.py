"""User — an authenticated application user (physician or admin)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.patient_user_access import PatientUserAccess


class User(TimestampMixin, Base):
    """A login account. MVP roles: ``doctor`` (assigned patients only) and
    ``admin`` (all patients). Passwords are stored ONLY as bcrypt hashes —
    the hash is never returned by the API or logged.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.doctor,
        server_default="doctor",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    patient_access: Mapped[list[PatientUserAccess]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
