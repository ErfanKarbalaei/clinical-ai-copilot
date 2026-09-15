"""Pydantic schemas for the document API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnalysisStatus, DocumentType, ExtractionStatus


class DocumentUpdate(BaseModel):
    """Payload for partially updating document metadata (PATCH).

    Only metadata is editable — the original file itself is never modified.
    """

    title: str | None = Field(default=None, min_length=1, max_length=300)
    doc_type: DocumentType | None = None


class DocumentResponse(BaseModel):
    """Document metadata returned by the API.

    ``storage_key`` is intentionally not exposed — clients use the
    ``/download`` endpoint (presigned URL) to fetch the original file.
    """

    id: int
    patient_id: int
    title: str
    doc_type: DocumentType
    file_name: str
    mime_type: str
    file_size_bytes: int
    extraction_status: ExtractionStatus
    extracted_text: str | None
    analysis_status: AnalysisStatus
    ai_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
