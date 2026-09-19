"""OtpRequest — a hashed, short-lived phone OTP (Task 21).

The plaintext code is NEVER stored — only a SHA-256 hash of phone+code.
One active OTP per phone (a new request supersedes the previous row).
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class OtpRequest(TimestampMixin, Base):
    __tablename__ = "otp_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts_left: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5"
    )

    def __repr__(self) -> str:
        return f"<OtpRequest id={self.id} phone=***>"
