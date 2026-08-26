"""Document API tests (require PostgreSQL; object storage is faked)."""

import pytest
from sqlalchemy import select

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.api.v1.routes import documents as documents_routes
from app.api.v1.routes.documents import (
    DOCUMENT_NOT_FOUND_DETAIL,
    INVALID_FILE_TYPE_DETAIL,
    STORAGE_UNAVAILABLE_DETAIL,
)
from app.models import ClinicalEvent
from app.services import documents as documents_service
from app.services import storage
from app.services.storage import StorageError
from tests.pdf_helper import pdf_with_text

PATIENTS_URL = "/api/v1/patients"
DOCUMENTS_NESTED_URL = "/api/v1/patients/{patient_id}/documents"
DOCUMENTS_ITEM_URL = "/api/v1/documents/{document_id}"

PDF_BYTES = b"%PDF-1.7 fake-clinical-report-body"
PDF_FILE = {"file": ("lab-report.pdf", PDF_BYTES, "application/pdf")}


@pytest.fixture()
def uploaded_keys(monkeypatch, db_session):
    """Fake the storage layer; record every key and serve its bytes back."""
    keys: list[str] = []
    deleted_keys: list[str] = []
    stored: dict[str, bytes] = {}

    def fake_upload(*, patient_id, file_name, content_type, data):
        key = f"patients/{patient_id}/documents/fake-{len(keys) + 1}-{file_name}"
        keys.append(key)
        stored[key] = data
        return key

    monkeypatch.setattr(storage, "upload_file", fake_upload)
    monkeypatch.setattr(storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(
        storage,
        "presigned_download_url",
        lambda key, expires=None: f"http://minio.test/{key}?sig=fake",
    )
    monkeypatch.setattr(
        storage, "get_object_bytes", lambda key: stored[key]  # noqa: B023
    )
    # Run the real extraction pipeline against the isolated test session.
    monkeypatch.setattr(
        documents_routes,
        "process_document",
        lambda document_id: documents_service.process_document(
            document_id, db=db_session
        ),
    )
    return keys, deleted_keys


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"سند {suffix}"}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _upload(api_client, patient_id: int, files=None, data=None):
    return api_client.post(
        DOCUMENTS_NESTED_URL.format(patient_id=patient_id),
        files=files or PDF_FILE,
        data=data or {},
    )


# --- upload ---


def test_upload_document_returns_201_with_metadata(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱")

    response = _upload(
        api_client,
        patient["id"],
        data={"title": "آزمایش خون", "doc_type": "lab_report"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["patient_id"] == patient["id"]
    assert body["title"] == "آزمایش خون"
    assert body["doc_type"] == "lab_report"
    assert body["file_name"] == "lab-report.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["file_size_bytes"] == len(PDF_BYTES)
    assert body["extraction_status"] == "pending"  # extraction is a later phase
    assert body["extracted_text"] is None
    assert "storage_key" not in body  # internal detail, not exposed
    assert uploaded_keys[0], "object was 'stored'"


def test_upload_defaults_title_to_file_name(api_client, make_patient, uploaded_keys):
    patient = make_patient("۲")

    body = _upload(api_client, patient["id"]).json()

    assert body["title"] == "lab-report.pdf"
    assert body["doc_type"] == "other"


def test_upload_creates_timeline_event(api_client, make_patient, db_session, uploaded_keys):
    patient = make_patient("۳")

    body = _upload(api_client, patient["id"]).json()

    events = db_session.scalars(
        select(ClinicalEvent).where(
            ClinicalEvent.source_type == "document",
            ClinicalEvent.source_id == body["id"],
        )
    ).all()
    assert len(events) == 1
    assert events[0].event_type == "document_uploaded"
    assert body["title"] in events[0].title


def test_upload_rejects_disallowed_mime_type(api_client, make_patient, uploaded_keys):
    patient = make_patient("۴")

    response = _upload(
        api_client,
        patient["id"],
        files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == INVALID_FILE_TYPE_DETAIL
    assert not uploaded_keys[0], "nothing stored on rejection"


def test_upload_rejects_empty_file(api_client, make_patient, uploaded_keys):
    patient = make_patient("۵")

    response = _upload(
        api_client,
        patient["id"],
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 422


def test_upload_rejects_oversized_file(api_client, make_patient, uploaded_keys, monkeypatch):
    patient = make_patient("۶")
    monkeypatch.setattr(documents_routes, "MAX_FILE_SIZE_BYTES", 10)

    response = _upload(
        api_client,
        patient["id"],
        files={"file": ("big.pdf", b"x" * 11, "application/pdf")},
    )

    assert response.status_code == 422


def test_upload_for_missing_patient_returns_404(api_client, uploaded_keys):
    response = _upload(api_client, 999999)

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


def test_upload_returns_503_when_storage_fails(api_client, make_patient, monkeypatch):
    patient = make_patient("۷")

    def broken_upload(**kwargs):
        raise StorageError("minio down")

    monkeypatch.setattr(storage, "upload_file", broken_upload)

    response = _upload(api_client, patient["id"])

    assert response.status_code == 503
    assert response.json()["detail"] == STORAGE_UNAVAILABLE_DETAIL


# --- list / get ---


def test_list_documents_scoped_and_newest_first(api_client, make_patient, uploaded_keys):
    patient = make_patient("۸")
    other = make_patient("۹")
    first = _upload(api_client, patient["id"]).json()
    _upload(api_client, other["id"])  # different patient — must not appear
    second = _upload(api_client, patient["id"]).json()

    response = api_client.get(DOCUMENTS_NESTED_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [second["id"], first["id"]]


def test_get_document_metadata_and_missing(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱۰")
    document = _upload(api_client, patient["id"]).json()

    ok = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=document["id"]))
    assert ok.status_code == 200
    assert ok.json()["id"] == document["id"]

    missing = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == DOCUMENT_NOT_FOUND_DETAIL


# --- download ---


def test_download_redirects_to_presigned_url(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱۱")
    document = _upload(api_client, patient["id"]).json()

    response = api_client.get(
        DOCUMENTS_ITEM_URL.format(document_id=document["id"]) + "/download",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith("http://minio.test/patients/")


# --- patch ---


def test_patch_document_metadata(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱۲")
    document = _upload(api_client, patient["id"]).json()

    response = api_client.patch(
        DOCUMENTS_ITEM_URL.format(document_id=document["id"]),
        json={"title": "گزارش رادیوگرافی", "doc_type": "imaging_report"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "گزارش رادیوگرافی"
    assert body["doc_type"] == "imaging_report"
    assert body["file_name"] == "lab-report.pdf"  # untouched


def test_patch_missing_document_returns_404(api_client):
    response = api_client.patch(
        DOCUMENTS_ITEM_URL.format(document_id=999999), json={"title": "x"}
    )

    assert response.status_code == 404


# --- delete ---


def test_delete_document_removes_metadata_object_and_event(
    api_client, make_patient, uploaded_keys, db_session
):
    keys, deleted_keys = uploaded_keys
    patient = make_patient("۱۳")
    document = _upload(api_client, patient["id"]).json()
    url = DOCUMENTS_ITEM_URL.format(document_id=document["id"])

    response = api_client.delete(url)

    assert response.status_code == 204
    assert api_client.get(url).status_code == 404
    assert deleted_keys == keys  # object removed from storage
    remaining_events = db_session.scalars(
        select(ClinicalEvent).where(ClinicalEvent.source_id == document["id"])
    ).all()
    assert remaining_events == []  # timeline entry removed too


def test_delete_missing_document_returns_404(api_client):
    response = api_client.delete(DOCUMENTS_ITEM_URL.format(document_id=999999))

    assert response.status_code == 404


# --- extraction pipeline (background task, deterministic tools) ---


def test_upload_response_starts_as_pending_then_extracts(api_client, make_patient, uploaded_keys):
    """The upload response says `pending`; the background task completes it."""
    patient = make_patient("۱۴")

    created = _upload(api_client, patient["id"], PDF_FILE).json()
    assert created["extraction_status"] == "pending"  # task runs after response

    # TestClient runs background tasks synchronously — fetch the outcome.
    final = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()
    # The fake PDF is not parseable → deterministic failure, no crash.
    assert final["extraction_status"] == "failed"
    assert final["extracted_text"] is None


def test_upload_text_file_extracts_inline(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱۵")

    created = _upload(
        api_client,
        patient["id"],
        {"file": ("note.txt", "HbA1c: 8.2 percent".encode(), "text/plain")},
    ).json()

    final = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()
    assert final["extraction_status"] == "completed"
    assert final["extracted_text"] == "HbA1c: 8.2 percent"


def test_upload_pdf_with_text_layer_extracts(api_client, make_patient, uploaded_keys):
    patient = make_patient("۱۶")

    created = _upload(
        api_client,
        patient["id"],
        {"file": ("lab.pdf", pdf_with_text("CLINICAL LAB REPORT WITH DETAILED PATIENT RESULTS 2026"), "application/pdf")},
    ).json()

    final = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()
    assert final["extraction_status"] == "completed"
    assert "CLINICAL LAB REPORT" in final["extracted_text"]


def test_storage_outage_during_extraction_marks_failed(api_client, make_patient, uploaded_keys, monkeypatch):
    patient = make_patient("۱۷")
    created = _upload(api_client, patient["id"], PDF_FILE).json()

    def broken_download(key):
        raise StorageError("minio down")

    monkeypatch.setattr(storage, "get_object_bytes", broken_download)
    response = api_client.post(
        DOCUMENTS_ITEM_URL.format(document_id=created["id"]) + "/extract"
    )

    assert response.status_code == 202
    final = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()
    assert final["extraction_status"] == "failed"


def test_reextract_endpoint_and_404s(api_client, make_patient, uploaded_keys, monkeypatch):
    patient = make_patient("۱۸")
    created = _upload(
        api_client,
        patient["id"],
        {"file": ("broken.pdf", b"%PDF-garbage", "application/pdf")},
    ).json()
    assert (
        api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()[
            "extraction_status"
        ]
        == "failed"
    )

    # Fix the "storage" so the same document now extracts successfully.
    fixed = pdf_with_text("SECOND ATTEMPT REPORT WITH FULL CLINICAL TEXT CONTENT")
    monkeypatch.setattr(storage, "get_object_bytes", lambda key: fixed)

    response = api_client.post(
        DOCUMENTS_ITEM_URL.format(document_id=created["id"]) + "/extract"
    )
    assert response.status_code == 202

    final = api_client.get(DOCUMENTS_ITEM_URL.format(document_id=created["id"])).json()
    assert final["extraction_status"] == "completed"
    assert "SECOND ATTEMPT REPORT" in final["extracted_text"]

    missing = api_client.post("/api/v1/documents/999999/extract")
    assert missing.status_code == 404