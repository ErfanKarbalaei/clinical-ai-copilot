"""Patient context + clinical timeline API tests (require PostgreSQL)."""

from datetime import date

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.models import Document, LabResult, VoiceNote
from app.models.enums import ExtractionStatus, TranscriptionStatus

PATIENTS_URL = "/api/v1/patients"
CONTEXT_URL = "/api/v1/patients/{patient_id}/context"
TIMELINE_URL = "/api/v1/patients/{patient_id}/timeline"


def _make_patient(api_client, suffix: str) -> dict:
    response = api_client.post(
        PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"زمینه {suffix}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- patient context ---


def test_context_for_patient_with_rich_data(api_client, db_session):
    patient = _make_patient(api_client, "۱")
    pid = patient["id"]

    api_client.post(
        f"{PATIENTS_URL}/{pid}/conditions", json={"name": "دیابت نوع ۲", "onset_date": "2024-03-01"}
    ).raise_for_status()
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Metformin 500"}
    ).raise_for_status()
    api_client.post(
        f"{PATIENTS_URL}/{pid}/allergies", json={"allergen": "پنی‌سیلین", "severity": "severe"}
    ).raise_for_status()
    db_session.add(
        LabResult(
            patient_id=pid, test_name="HbA1c", value="8.2", unit="%",
            reference_range="4.0-6.0", flag="abnormal", result_date=date(2026, 7, 1),
        )
    )
    db_session.add(
        Document(
            patient_id=pid,
            title="گزارش آزمایش",
            storage_key=f"patients/{pid}/documents/test-ctx.pdf",
            file_name="report.pdf",
            mime_type="application/pdf",
            file_size_bytes=128,
            extraction_status=ExtractionStatus.completed,
            extracted_text="GLUCOSE LEVELS TYPED REPORT",
        )
    )
    db_session.add(
        VoiceNote(
            patient_id=pid,
            title="یادداشت صوتی ویزیت",
            audio_storage_key=f"patients/{pid}/voice/test-ctx.webm",
            duration_seconds=30,
            transcription_status=TranscriptionStatus.completed,
            transcript="بیمار سابقه دیابت دارد و متفورمین مصرف می‌کند.",
        )
    )
    db_session.commit()

    response = api_client.get(CONTEXT_URL.format(patient_id=pid))

    assert response.status_code == 200
    context = response.json()
    assert context["patient"]["id"] == pid
    assert context["patient"]["first_name"] == "آزمون"
    assert [c["name"] for c in context["conditions"]] == ["دیابت نوع ۲"]
    assert len(context["medications"]) == 1
    assert context["medications"][0]["medication"]["name"] == "Metformin 500"
    assert context["allergies"][0]["severity"] == "severe"
    assert context["lab_results"][0]["test_name"] == "HbA1c"
    # document extracted text is included for the future AI context
    assert any(
        "GLUCOSE LEVELS" in (doc["extracted_text"] or "")
        for doc in context["documents"]
    )
    # raw voice-note transcript is included
    assert any(
        "متفورمین" in (vn["transcript"] or "") for vn in context["voice_notes"]
    )
    assert "generated_at" in context


def test_context_medications_include_history(api_client):
    patient = _make_patient(api_client, "۲")
    pid = patient["id"]
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Drug Active"}
    ).raise_for_status()
    stopped = api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Drug Old"}
    ).json()
    api_client.patch(
        f"/api/v1/patient-medications/{stopped['id']}",
        json={"status": "stopped"},
    ).raise_for_status()

    context = api_client.get(CONTEXT_URL.format(patient_id=pid)).json()

    statuses = [m["status"] for m in context["medications"]]
    assert statuses == ["active", "stopped"]  # active first, history kept


def test_context_for_patient_without_any_data(api_client):
    patient = _make_patient(api_client, "۳")

    response = api_client.get(CONTEXT_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    context = response.json()
    assert context["patient"]["id"] == patient["id"]
    for section in (
        "conditions", "medications", "allergies",
        "lab_results", "documents", "voice_notes", "clinical_notes",
    ):
        assert context[section] == [], section


def test_context_missing_patient_returns_404(api_client):
    response = api_client.get(CONTEXT_URL.format(patient_id=999999))

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


# --- clinical timeline ---


def test_timeline_chronological_ordering_with_mixed_dates(api_client, db_session):
    patient = _make_patient(api_client, "۴")
    pid = patient["id"]
    # distinct controllable primary dates
    api_client.post(
        f"{PATIENTS_URL}/{pid}/conditions", json={"name": "آسم", "onset_date": "2025-06-01"}
    ).raise_for_status()
    db_session.add(
        LabResult(patient_id=pid, test_name="FBS", value="110", result_date=date(2026, 1, 1))
    )
    db_session.commit()
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications",
        json={"medication_name": "Ventolin", "start_date": "2026-02-01"},
    ).raise_for_status()
    # created_at = now → newest
    api_client.post(
        f"{PATIENTS_URL}/{pid}/documents",
        files={"file": ("r.txt", "REPORT".encode(), "text/plain")},
    ).raise_for_status()

    response = api_client.get(TIMELINE_URL.format(patient_id=pid))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["items"]) == 4
    event_types = [item["event_type"] for item in body["items"]]
    # newest first: document (now) → medication (2026-02) → lab (2026-01) → condition (2025-06)
    assert event_types == [
        "document_uploaded", "medication_started", "lab_result", "condition_onset",
    ]
    dates = [item["date"] for item in body["items"]]
    assert dates == sorted(dates, reverse=True)


def test_timeline_missing_dates_fall_back_to_created_at(api_client, db_session):
    patient = _make_patient(api_client, "۵")
    pid = patient["id"]
    # lab WITHOUT result_date → must still appear, dated by created_at
    db_session.add(LabResult(patient_id=pid, test_name="CRP", value="5"))
    # medication WITHOUT start_date → appears via created_at
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Undated Med"}
    ).raise_for_status()
    db_session.commit()

    items = api_client.get(TIMELINE_URL.format(patient_id=pid)).json()["items"]

    assert {item["event_type"] for item in items} == {"lab_result", "medication_started"}
    assert all(item["date"] is not None for item in items)


def test_timeline_includes_resolution_and_stop_events(api_client):
    patient = _make_patient(api_client, "۶")
    pid = patient["id"]
    condition = api_client.post(
        f"{PATIENTS_URL}/{pid}/conditions",
        json={"name": "برونشیت", "onset_date": "2026-01-01"},
    ).json()
    api_client.patch(
        f"/api/v1/conditions/{condition['id']}",
        json={"status": "resolved", "resolved_date": "2026-02-01"},
    ).raise_for_status()
    med = api_client.post(
        f"{PATIENTS_URL}/{pid}/medications",
        json={"medication_name": "Azithro", "start_date": "2026-01-02"},
    ).json()
    api_client.patch(
        f"/api/v1/patient-medications/{med['id']}",
        json={"status": "stopped", "end_date": "2026-01-20"},
    ).raise_for_status()

    items = api_client.get(TIMELINE_URL.format(patient_id=pid)).json()["items"]

    assert {item["event_type"] for item in items} == {
        "condition_onset", "condition_resolved",
        "medication_started", "medication_stopped",
    }
    resolved = next(i for i in items if i["event_type"] == "condition_resolved")
    assert resolved["date"] >= "2026-02-01" or resolved["date"].startswith("2026-02-01")


def test_timeline_items_carry_source_references(api_client):
    patient = _make_patient(api_client, "۷")
    pid = patient["id"]
    doc = api_client.post(
        f"{PATIENTS_URL}/{pid}/documents",
        files={"file": ("r.txt", "X".encode(), "text/plain")},
    ).json()

    items = api_client.get(TIMELINE_URL.format(patient_id=pid)).json()["items"]

    assert items[0]["source_type"] == "document"
    assert items[0]["source_id"] == doc["id"]
    assert items[0]["title"].startswith("سند:")


def test_timeline_empty_for_new_patient_and_404(api_client):
    patient = _make_patient(api_client, "۸")

    response = api_client.get(TIMELINE_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}

    missing = api_client.get(TIMELINE_URL.format(patient_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == PATIENT_NOT_FOUND_DETAIL
