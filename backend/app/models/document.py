"""Document — metadata for an uploaded clinical document."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import DocumentType, ExtractionStatus

if TYPE_CHECKING:
    from app.models.patient import Patient


class Document(TimestampMixin, Base):
    """Metadata for an uploaded clinical document (lab report, imaging, ...).

    The original file itself lives in object storage (MinIO) at
    ``storage_key`` — it is preserved unchanged and is always the source of
    truth. ``extracted_text`` is derived data used for search/AI context and
    never replaces the original.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"),
        default=DocumentType.other,
        server_default="other",
    )
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    file_name: Mapped[str] = mapped_column(String(300))  # original upload filename
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        SAEnum(ExtractionStatus, name="extraction_status"),
        default=ExtractionStatus.pending,
        server_default="pending",
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)

    patient: Mapped[Patient] = relationship(back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} patient_id={self.patient_id} title={self.title!r}>"
