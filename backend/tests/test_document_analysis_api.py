"""Document AI-analysis tests (provider mocked — no real LLM calls)."""

import pytest

from app.api.v1.routes.documents import (
    AI_NOT_CONFIGURED_DETAIL,
    AI_PROVIDER_ERROR_DETAIL,
    ANALYSIS_NEEDS_EXTRACTION_DETAIL,
    DOCUMENT_NOT_FOUND_DETAIL,
)
from app.models import Document
from app.models.enums import AnalysisStatus, ExtractionStatus
from app.services import ai
from app.services.document_analysis import (
    _MAX_EXTRACTED_CHARS,
    build_analysis_message,
)

PATIENTS_URL = "/api/v1/patients"
ANALYZE_URL = "/api/v1/documents/{document_id}/analyze"

CAPTURED: dict = {}


class FakeProvider:
    def complete(self, *, system, user, history=None):
        CAPTURED["system"] = system
        CAPTURED["user"] = user
        return "  یافته‌های کلیدی: …  "

    @classmethod
    def reset(cls):
        CAPTURED.clear()


@pytest.fixture()
def fake_provider(monkeypatch):
    FakeProvider.reset()
    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    return FakeProvider


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"تحلیل {suffix}"}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _make_document(db_session, patient_id: int, *, extracted: str | None, key: str) -> Document:
    document = Document(
        patient_id=patient_id,
        title="گزارش آزمایش",
        storage_key=key,
        file_name="lab.pdf",
        mime_type="application/pdf",
        file_size_bytes=128,
        extraction_status=(
            ExtractionStatus.completed if extracted else ExtractionStatus.pending
        ),
        extracted_text=extracted,
    )
    db_session.add(document)
    db_session.commit()
    return document


# --- prompt building ---


def test_build_analysis_message_grounded_and_capped(db_session, make_patient, api_client):
    patient = make_patient("۱")
    document = _make_document(
        db_session, patient["id"],
        extracted="HbA1c: 8.2 %" + "x" * (_MAX_EXTRACTED_CHARS + 500),
        key="k-cap",
    )

    message = build_analysis_message(document)

    assert "HbA1c: 8.2" in message
    assert "گزارش آزمایش" in message  # title for context
    assert len(message) < _MAX_EXTRACTED_CHARS + 500  # capped
    assert "بریده شد" in message


def test_analysis_prompt_is_safety_scoped():
    from app.services.document_analysis import DOCUMENT_ANALYSIS_PROMPT

    assert "never invent" in DOCUMENT_ANALYSIS_PROMPT
    assert "یافته‌های کلیدی" in DOCUMENT_ANALYSIS_PROMPT


# --- API ---


def test_analyze_document_returns_persian_summary(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۲")
    document = _make_document(
        db_session, patient["id"], extracted="FBS 168 mg/dL, HbA1c 8.2 %", key="k-ok"
    )

    response = api_client.post(ANALYZE_URL.format(document_id=document.id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_summary"] == "یافته‌های کلیدی: …"  # stripped
    assert body["analysis_status"] == "completed"
    # prompt grounded in the extracted text, original untouched
    assert "FBS 168" in CAPTURED["user"]
    assert "never invent" in CAPTURED["system"]
    refreshed = db_session.get(Document, document.id)
    assert refreshed.extracted_text == "FBS 168 mg/dL, HbA1c 8.2 %"


def test_analyze_requires_completed_extraction(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۳")
    pending = _make_document(db_session, patient["id"], extracted=None, key="k-pending")
    empty = _make_document(db_session, patient["id"], extracted="   ", key="k-empty")
    db_session.get(Document, empty.id).extraction_status = ExtractionStatus.completed
    db_session.commit()

    for document in (pending, empty):
        response = api_client.post(ANALYZE_URL.format(document_id=document.id))
        assert response.status_code == 409
        assert response.json()["detail"] == ANALYSIS_NEEDS_EXTRACTION_DETAIL


def test_analyze_overwrites_previous_summary(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۴")
    document = _make_document(db_session, patient["id"], extracted="Vitamin D 12 ng/ml", key="k-re")
    first = api_client.post(ANALYZE_URL.format(document_id=document.id)).json()
    assert first["analysis_status"] == "completed"

    second = api_client.post(ANALYZE_URL.format(document_id=document.id)).json()

    assert second["analysis_status"] == "completed"
    assert second["ai_summary"]  # fresh summary present


def test_analyze_provider_failure_marks_failed_keeps_original(
    api_client, db_session, make_patient, monkeypatch
):
    patient = make_patient("۵")
    document = _make_document(db_session, patient["id"], extracted="LDL 140", key="k-502")

    class BrokenProvider:
        def complete(self, **kwargs):
            raise ai.AIError("boom")

    monkeypatch.setattr(ai, "get_provider", lambda: BrokenProvider())

    response = api_client.post(ANALYZE_URL.format(document_id=document.id))

    assert response.status_code == 502
    assert response.json()["detail"] == AI_PROVIDER_ERROR_DETAIL
    refreshed = db_session.get(Document, document.id)
    assert refreshed.analysis_status == AnalysisStatus.failed
    assert refreshed.ai_summary is None
    assert refreshed.extracted_text == "LDL 140"  # source of truth intact


def test_analyze_without_key_returns_503(api_client, db_session, make_patient, monkeypatch):
    patient = make_patient("۶")
    document = _make_document(db_session, patient["id"], extracted="text", key="k-503")

    def unavailable():
        raise ai.AIUnavailableError("no key")

    monkeypatch.setattr(ai, "get_provider", unavailable)

    response = api_client.post(ANALYZE_URL.format(document_id=document.id))

    assert response.status_code == 503
    assert response.json()["detail"] == AI_NOT_CONFIGURED_DETAIL


def test_analyze_missing_document_404(api_client):
    response = api_client.post(ANALYZE_URL.format(document_id=999999))
    assert response.status_code == 404
    assert response.json()["detail"] == DOCUMENT_NOT_FOUND_DETAIL


def test_document_endpoints_expose_analysis_fields(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۷")
    document = _make_document(db_session, patient["id"], extracted="Hb 13.5", key="k-fields")

    listing = api_client.get(f"{PATIENTS_URL}/{patient['id']}/documents").json()
    assert listing[0]["analysis_status"] == "pending"  # default
    assert listing[0]["ai_summary"] is None

    analyzed = api_client.post(ANALYZE_URL.format(document_id=document.id)).json()
    fetched = api_client.get(f"/api/v1/documents/{document.id}").json()
    assert fetched["analysis_status"] == analyzed["analysis_status"] == "completed"
    assert fetched["ai_summary"] == analyzed["ai_summary"]


def test_patient_context_includes_ai_summary(api_client, db_session, make_patient, fake_provider):
    patient = make_patient("۸")
    document = _make_document(db_session, patient["id"], extracted="TSH 2.4", key="k-ctx")

    api_client.post(ANALYZE_URL.format(document_id=document.id)).raise_for_status()

    context = api_client.get(f"{PATIENTS_URL}/{patient['id']}/context").json()
    doc_in_context = next(
        d for d in context["documents"] if d["id"] == document.id
    )
    assert doc_in_context["ai_summary"] == "یافته‌های کلیدی: …"
    assert doc_in_context["analysis_status"] == "completed"


def test_server_default_pending_via_raw_insert(db_session, make_patient, api_client):
    """The migration's server_default backfills pre-existing rows to pending."""
    from sqlalchemy import text

    patient = make_patient("۹")
    db_session.execute(
        text(
            "INSERT INTO documents (patient_id, title, storage_key, file_name,"
            " mime_type, file_size_bytes, extraction_status)"
            " VALUES (:pid, 'legacy', 'k-legacy', 'f.pdf', 'application/pdf',"
            " 1, 'completed')"
        ),
        {"pid": patient["id"]},
    )
    db_session.commit()

    listing = api_client.get(f"{PATIENTS_URL}/{patient['id']}/documents").json()
    legacy = next(d for d in listing if d["title"] == "legacy")
    assert legacy["analysis_status"] == "pending"  # server default applied
    assert legacy["ai_summary"] is None
