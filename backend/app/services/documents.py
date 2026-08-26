"""Document processing orchestration: extraction status lifecycle.

Runs as a FastAPI background task after upload (and on manual re-extract).
Opens its own database session because the request session is already
closed by the time background tasks execute.
"""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Document
from app.models.enums import ExtractionStatus
from app.services import extraction, storage

logger = logging.getLogger(__name__)


def process_document(document_id: int, db: Session | None = None) -> None:
    """Extract text for one document and persist the outcome.

    Status lifecycle: pending → processing → completed | failed.
    Never raises — a broken extraction (or a document deleted concurrently)
    must not crash the background task.
    """
    if db is None:
        with SessionLocal() as session:
            _process(session, document_id)
        return
    _process(db, document_id)


def _process(db: Session, document_id: int) -> None:
    document = db.get(Document, document_id)
    if document is None:
        logger.warning("process_document: document %s not found", document_id)
        return

    try:
        document.extraction_status = ExtractionStatus.processing
        db.commit()

        data = storage.get_object_bytes(document.storage_key)
        result = extraction.extract_text(
            mime_type=document.mime_type, data=data
        )
        document.extracted_text = result.text.strip() or None
        document.extraction_status = ExtractionStatus.completed
        db.commit()
        logger.info(
            "extraction ok (document=%s, method=%s, %d chars)",
            document_id, result.method, len(result.text),
        )
    except SQLAlchemyError as error:
        # e.g. the document was deleted while this task was running.
        db.rollback()
        logger.warning(
            "extraction aborted — document %s changed/deleted concurrently: %s",
            document_id,
            error,
        )
    except Exception as error:  # noqa: BLE001 — any failure → failed status
        document.extracted_text = None
        document.extraction_status = ExtractionStatus.failed
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        logger.warning("extraction failed (document=%s): %s", document_id, error)
