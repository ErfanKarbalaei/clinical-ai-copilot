"""VoiceNote — a clinical voice recording."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import ConversationType, TranscriptionStatus

if TYPE_CHECKING:
    from app.models.patient import Patient


class VoiceNote(TimestampMixin, Base):
    """A clinical voice recording: either a physician note or a
    doctor–patient conversation.

    The original audio lives in object storage at ``audio_storage_key`` and
    is preserved unchanged. ``transcript`` holds the raw speech-to-text
    output (derived data) — it is kept as produced; reviewed/edited content
    becomes a ClinicalNote instead.
    """

    __tablename__ = "voice_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(300))
    conversation_type: Mapped[ConversationType] = mapped_column(
        SAEnum(ConversationType, name="conversation_type"),
        default=ConversationType.physician_note,
        server_default="physician_note",
    )
    audio_storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(10), default="fa", server_default="fa")
    transcription_status: Mapped[TranscriptionStatus] = mapped_column(
        SAEnum(TranscriptionStatus, name="transcription_status"),
        default=TranscriptionStatus.pending,
        server_default="pending",
    )
    transcript: Mapped[Optional[str]] = mapped_column(Text)

    patient: Mapped[Patient] = relationship(back_populates="voice_notes")

    def __repr__(self) -> str:
        return f"<VoiceNote id={self.id} patient_id={self.patient_id} title={self.title!r}>"
