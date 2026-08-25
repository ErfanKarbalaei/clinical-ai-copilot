"""MinIO (S3-compatible) object storage service.

Stores the ORIGINAL clinical files unchanged — the database only keeps
metadata plus the object key (see the Document model). All MinIO
interactions are wrapped so route handlers never see SDK exceptions.
"""

import io
import re
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()


class StorageError(Exception):
    """Raised when object storage is unreachable or rejects an operation."""


_client: Minio | None = None


def get_client() -> Minio:
    """Lazy singleton MinIO client (created on first use, no connection)."""
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def _bucket() -> str:
    return settings.MINIO_BUCKET


def ensure_bucket() -> None:
    """Create the documents bucket if it does not exist yet."""
    try:
        client = get_client()
        if not client.bucket_exists(_bucket()):
            client.make_bucket(_bucket())
    except S3Error as error:
        raise StorageError(f"bucket check/creation failed: {error}") from None


_UNSAFE_CHARS = re.compile(r"[^\w.\-]+", re.UNICODE)
_CONSECUTIVE_DOTS = re.compile(r"\.{2,}")
_MAX_NAME_LENGTH = 150


def build_storage_key(patient_id: int, file_name: str) -> str:
    """Deterministic, unique object key: patients/{id}/documents/{uuid}-{name}."""
    # Strip any path components, replace unsafe characters and collapse dots.
    base_name = file_name.replace("\\", "/").rsplit("/", 1)[-1] or "file"
    safe_name = _UNSAFE_CHARS.sub("_", base_name)
    safe_name = _CONSECUTIVE_DOTS.sub(".", safe_name).lstrip(".")
    safe_name = safe_name[:_MAX_NAME_LENGTH] or "file"
    return f"patients/{patient_id}/documents/{uuid.uuid4().hex}-{safe_name}"


def upload_file(
    *, patient_id: int, file_name: str, content_type: str, data: bytes
) -> str:
    """Upload the original file and return its storage key."""
    key = build_storage_key(patient_id, file_name)
    try:
        client = get_client()
        if not client.bucket_exists(_bucket()):
            client.make_bucket(_bucket())
        client.put_object(
            _bucket(),
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
    except S3Error as error:
        raise StorageError(f"upload failed: {error}") from None
    return key


def delete_object(storage_key: str) -> None:
    """Delete an object; a missing object is treated as success."""
    try:
        get_client().remove_object(_bucket(), storage_key)
    except S3Error as error:
        raise StorageError(f"delete failed: {error}") from None


def presigned_download_url(
    storage_key: str, expires: timedelta = timedelta(hours=1)
) -> str:
    """Short-lived presigned URL so browsers download straight from MinIO."""
    try:
        return get_client().presigned_get_object(
            _bucket(), storage_key, expires=expires
        )
    except S3Error as error:
        raise StorageError(f"presigned URL failed: {error}") from None
