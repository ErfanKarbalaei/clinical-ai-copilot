"""ClinicalNote — a note reviewed/confirmed as part of the record."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import NoteSource

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.voice_note import VoiceNote


class ClinicalNote(TimestampMixin, Base):
    """A clinical note that is part of the patient record.

    ``source`` records where the note came from. When it was derived from a
    voice recording, ``voice_note_id`` keeps the link to the original audio
    (traceability: derived data must point back to its source).
    """

    __tablename__ = "clinical_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    voice_note_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("voice_notes.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[NoteSource] = mapped_column(
        SAEnum(NoteSource, name="note_source"),
        default=NoteSource.manual,
        server_default="manual",
    )

    patient: Mapped[Patient] = relationship(back_populates="clinical_notes")
    voice_note: Mapped[Optional[VoiceNote]] = relationship()

    def __repr__(self) -> str:
        return f"<ClinicalNote id={self.id} patient_id={self.patient_id} title={self.title!r}>"
