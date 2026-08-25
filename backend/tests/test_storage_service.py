"""Integration tests for the MinIO storage service.

Skipped automatically when MinIO is not reachable (same pattern as the
database tests) — start it with: docker compose up -d minio
"""

import pytest

from app.services import storage
from app.services.storage import StorageError


@pytest.fixture(scope="module")
def minio_available():
    try:
        storage.ensure_bucket()
    except StorageError as error:
        pytest.skip(f"MinIO is not reachable ({error}). Start it with: docker compose up -d minio")
    return True


def test_upload_presign_download_delete_roundtrip(minio_available):
    payload = b"%PDF-1.7 real-roundtrip-document"
    key = storage.upload_file(
        patient_id=0,
        file_name="roundtrip.pdf",
        content_type="application/pdf",
        data=payload,
    )

    assert key.startswith("patients/0/documents/")
    assert key.endswith("roundtrip.pdf")

    # The object exists with the exact original bytes.
    client = storage.get_client()
    stat = client.stat_object(storage.settings.MINIO_BUCKET, key)
    assert stat.size == len(payload)
    assert stat.content_type == "application/pdf"

    # Presigned URL fetches the original content.
    import urllib.request

    url = storage.presigned_download_url(key)
    with urllib.request.urlopen(url) as response:  # noqa: S310 (test-only URL)
        assert response.read() == payload

    storage.delete_object(key)
    listing = list(
        client.list_objects(storage.settings.MINIO_BUCKET, prefix=key)
    )
    assert listing == []


def test_storage_key_is_unique_and_sanitized(minio_available):
    key_a = storage.build_storage_key(7, "گزارش آزمایش ..pdf")
    key_b = storage.build_storage_key(7, "گزارش آزمایش ..pdf")
    assert key_a != key_b  # uuid prefix
    assert key_a.startswith("patients/7/documents/")
    # Persian characters are preserved (unicode word chars), spaces are not.
    assert " " not in key_a and ".." not in key_a.rsplit("/", 1)[-1].split("-", 1)[1]
