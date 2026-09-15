"""Optional AI analysis of a document's extracted text.

Reuses the existing provider-agnostic AI layer (Task 10 / 10.5). The
analysis is DERIVED data: it is stored on the document row for convenience
but never replaces the original file (object storage) or the extracted
text — both remain the source of truth.

MVP flow (synchronous, one provider call):

    extracted_text (deterministic, from Task 7)
        → provider.complete(document-analysis prompt)
        → Persian summary stored as ai_summary (analysis_status=completed)

No new tables, no queue, no RAG — just the existing abstractions.
"""

import logging

from sqlalchemy.orm import Session

from app.models import Document
from app.models.enums import AnalysisStatus
from app.services import ai

logger = logging.getLogger(__name__)

# Safety-scoped prompt for clinical-document summarization.
DOCUMENT_ANALYSIS_PROMPT = """You summarize clinical documents for a physician.
You receive one document's extracted text and its metadata (title/type).

Rules:
- Summarize ONLY what the text actually says; never invent findings, values,
  diagnoses, or medications that are not present in the text.
- If the text is empty, garbled, or contains no clinical content, say so
  explicitly instead of guessing.
- Structure (in Persian): «یافته‌های کلیدی» (bullet list), then «نکات قابل توجه»
  (bullet list), then one line starting with «محدودیت:» stating limitations.
- Keep lab values, drug names and units exactly as they appear (Latin form
  where the text uses it). Be concise: at most ~200 words.
- This is decision support only; the physician makes the final decision.
"""

# Cap on the extracted text sent to the provider (defense against huge files).
_MAX_EXTRACTED_CHARS = 20_000


def build_analysis_message(document: Document) -> str:
    """Serialize document metadata + capped extracted text for the provider."""
    text = (document.extracted_text or "").strip()
    if len(text) > _MAX_EXTRACTED_CHARS:
        text = text[:_MAX_EXTRACTED_CHARS] + "\n… [متن بریده شد]"
    return (
        f"Document title: {document.title}\n"
        f"Document type: {document.doc_type.value}\n"
        f"Extracted text:\n{text or '(خالی)'}"
    )


def analyze_document(document: Document, db: Session) -> Document:
    """Analyze one document's extracted text and persist the summary.

    Synchronous MVP: the caller (route) maps provider failures to HTTP 503/
    502 — a failed analysis leaves ``analysis_status=failed`` and the
    document (original + extracted text) fully intact.
    """
    summary = ai.get_provider().complete(
        system=DOCUMENT_ANALYSIS_PROMPT,
        user=build_analysis_message(document),
    )

    document.ai_summary = summary.strip() or None
    document.analysis_status = (
        AnalysisStatus.completed if document.ai_summary else AnalysisStatus.failed
    )
    db.commit()
    db.refresh(document)
    logger.info(
        "document analysis ok (document=%s, %d chars)",
        document.id, len(document.ai_summary or ""),
    )
    return document


def mark_analysis_failed(document: Document, db: Session) -> None:
    """Record a failed analysis attempt (original data stays untouched)."""
    document.ai_summary = None
    document.analysis_status = AnalysisStatus.failed
    db.commit()
