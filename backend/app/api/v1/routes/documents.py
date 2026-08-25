"""Patient document endpoints (API v1) — upload to object storage + metadata.

The original file is stored UNCHANGED in MinIO; PostgreSQL keeps only
metadata. Extracted text is a later (AI) phase — uploads start as
`extraction_status=pending`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import patient_from_id
from app.db.session import get_db
from app.models import ClinicalEvent, Document, Patient
from app.models.enums import DocumentType
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services import storage
from app.services.storage import StorageError

router = APIRouter(tags=["documents"])

DOCUMENT_NOT_FOUND_DETAIL = "سند یافت نشد."
INVALID_FILE_TYPE_DETAIL = "نوع فایل مجاز نیست. فرمت‌های مجاز: PDF، تصاویر (PNG/JPEG/WebP) و متن ساده."
FILE_TOO_LARGE_DETAIL = "حجم فایل بیش از حد مجاز است (حداکثر ۲۰ مگابایت)."
FILE_NAME_TOO_LONG_DETAIL = "نام فایل بیش از حد طولانی است."
STORAGE_UNAVAILABLE_DETAIL = "سرویس ذخیره‌سازی فایل در دسترس نیست."

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_FILE_NAME_LENGTH = 300


def _get_document_or_404(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=DOCUMENT_NOT_FOUND_DETAIL
        )
    return document


@router.post(
    "/patients/{patient_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a clinical document for a patient",
    description=(
        "Multipart upload: `file` (required) plus optional `title` and "
        "`doc_type` form fields. The original file is preserved unchanged "
        "in object storage; only metadata is stored in PostgreSQL. "
        "Allowed types: PDF, PNG, JPEG, WebP, plain text — max 20 MB."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "فایل نامعتبر"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "ذخیره‌سازی در دسترس نیست"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="فایل سند"),
    title: str | None = Form(default=None, description="عنوان (پیش‌فرض: نام فایل)"),
    doc_type: DocumentType | None = Form(default=None, description="نوع سند"),
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> Document:
    file_name = file.filename or "file"
    content_type = file.content_type or ""

    if len(file_name) > MAX_FILE_NAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=FILE_NAME_TOO_LONG_DETAIL,
        )
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=INVALID_FILE_TYPE_DETAIL,
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=FILE_TOO_LARGE_DETAIL,
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=INVALID_FILE_TYPE_DETAIL,
        )

    try:
        storage_key = storage.upload_file(
            patient_id=patient.id,
            file_name=file_name,
            content_type=content_type,
            data=data,
        )
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None

    document = Document(
        patient_id=patient.id,
        title=(title or file_name).strip() or file_name,
        doc_type=doc_type or DocumentType.other,
        storage_key=storage_key,
        file_name=file_name,
        mime_type=content_type,
        file_size_bytes=len(data),
    )
    db.add(document)
    db.flush()  # document.id needed for the timeline event

    db.add(
        ClinicalEvent(
            patient=patient,
            event_type="document_uploaded",
            event_date=datetime.now(timezone.utc),
            title=f"بارگذاری سند: {document.title}",
            source_type="document",
            source_id=document.id,
        )
    )
    db.commit()
    db.refresh(document)
    return document


@router.get(
    "/patients/{patient_id}/documents",
    response_model=list[DocumentResponse],
    summary="List a patient's documents",
    description="Newest first.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_documents(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[Document]:
    documents = db.scalars(
        select(Document)
        .where(Document.patient_id == patient.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
    ).all()
    return list(documents)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata by id",
    responses={status.HTTP_404_NOT_FOUND: {"description": DOCUMENT_NOT_FOUND_DETAIL}},
)
def get_document(document_id: int, db: Session = Depends(get_db)) -> Document:
    return _get_document_or_404(db, document_id)


@router.get(
    "/documents/{document_id}/download",
    summary="Download the original file",
    description=(
        "Redirects (307) to a short-lived presigned URL served directly by "
        "object storage — the original file is streamed unchanged."
    ),
    response_class=RedirectResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": DOCUMENT_NOT_FOUND_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": STORAGE_UNAVAILABLE_DETAIL},
    },
)
def download_document(
    document_id: int, db: Session = Depends(get_db)
) -> RedirectResponse:
    document = _get_document_or_404(db, document_id)
    try:
        url = storage.presigned_download_url(document.storage_key)
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Update document metadata (title / type)",
    description="Only metadata can be edited — the original file never changes.",
    responses={status.HTTP_404_NOT_FOUND: {"description": DOCUMENT_NOT_FOUND_DETAIL}},
)
def update_document(
    document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)
) -> Document:
    document = _get_document_or_404(db, document_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Removes the file from object storage, the metadata row, and its timeline event.",
    responses={status.HTTP_404_NOT_FOUND: {"description": DOCUMENT_NOT_FOUND_DETAIL}},
)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    document = _get_document_or_404(db, document_id)
    try:
        storage.delete_object(document.storage_key)
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None

    db.delete(document)
    # Remove the timeline entry pointing at the deleted document.
    db.execute(
        delete(ClinicalEvent).where(
            ClinicalEvent.source_type == "document",
            ClinicalEvent.source_id == document_id,
        )
    )
    db.commit()
