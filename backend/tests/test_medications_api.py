"""Patient medication API tests (require a running PostgreSQL)."""

from sqlalchemy import select

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.api.v1.routes.medications import (
    MEDICATION_NOT_FOUND_DETAIL,
    PATIENT_MEDICATION_NOT_FOUND_DETAIL,
)
from app.models import Medication

PATIENTS_URL = "/api/v1/patients"
MEDICATIONS_NESTED_URL = "/api/v1/patients/{patient_id}/medications"
PATIENT_MEDICATIONS_ITEM_URL = "/api/v1/patient-medications/{record_id}"


def _make_patient(api_client, suffix: str) -> dict:
    response = api_client.post(
        PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"دارو {suffix}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_medication_record(api_client, patient_id: int, **overrides) -> dict:
    payload = {
        "medication_name": "Metformin 500",
        "dosage": "500 mg",
        "frequency": "دو بار در روز",
        "start_date": "2026-01-01",
    }
    payload.update(overrides)
    response = api_client.post(
        MEDICATIONS_NESTED_URL.format(patient_id=patient_id), json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---


def test_create_patient_medication_by_name_creates_catalog_entry(api_client, db_session):
    patient = _make_patient(api_client, "۱")

    record = _create_medication_record(api_client, patient["id"])

    assert record["patient_id"] == patient["id"]
    assert record["status"] == "active"  # default
    assert record["medication"]["name"] == "Metformin 500"
    assert record["medication"]["id"] > 0
    catalog_count = len(
        db_session.scalars(
            select(Medication).where(Medication.name == "Metformin 500")
        ).all()
    )
    assert catalog_count == 1  # a catalog entry was created


def test_create_by_name_reuses_existing_catalog_entry(api_client):
    first_patient = _make_patient(api_client, "۲")
    second_patient = _make_patient(api_client, "۳")

    first = _create_medication_record(api_client, first_patient["id"])
    second = _create_medication_record(
        api_client, second_patient["id"], medication_name="metformin 500"
    )  # different case → same catalog entry

    assert second["medication"]["id"] == first["medication"]["id"]


def test_create_patient_medication_by_catalog_id(api_client, db_session):
    patient = _make_patient(api_client, "۴")
    db_session.add(Medication(name="Losartan 50", generic_name="Losartan"))
    db_session.flush()

    response = api_client.post(
        MEDICATIONS_NESTED_URL.format(patient_id=patient["id"]),
        json={"medication_id": db_session.scalars(
            select(Medication.id).where(Medication.name == "Losartan 50")
        ).one()},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["medication"]["name"] == "Losartan 50"
    assert body["medication"]["generic_name"] == "Losartan"


def test_create_with_unknown_catalog_id_returns_404(api_client):
    patient = _make_patient(api_client, "۵")

    response = api_client.post(
        MEDICATIONS_NESTED_URL.format(patient_id=patient["id"]),
        json={"medication_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == MEDICATION_NOT_FOUND_DETAIL


def test_create_requires_exactly_one_medication_reference(api_client):
    patient = _make_patient(api_client, "۶")
    url = MEDICATIONS_NESTED_URL.format(patient_id=patient["id"])

    neither = api_client.post(url, json={"dosage": "10 mg"})
    both = api_client.post(
        url, json={"medication_id": 1, "medication_name": "Metformin 500"}
    )

    assert neither.status_code == 422
    assert both.status_code == 422


def test_create_for_nonexistent_patient_returns_404(api_client):
    response = api_client.post(
        MEDICATIONS_NESTED_URL.format(patient_id=999999),
        json={"medication_name": "Metformin 500"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


# --- list: ordering, status filter, history ---


def test_list_orders_active_first_then_newest_and_keeps_history(api_client):
    patient = _make_patient(api_client, "۷")

    older_active = _create_medication_record(
        api_client, patient["id"], medication_name="Drug A", start_date="2020-01-01"
    )
    stopped = _create_medication_record(
        api_client,
        patient["id"],
        medication_name="Drug B",
        start_date="2024-01-01",
        status="stopped",
    )
    newer_active = _create_medication_record(
        api_client, patient["id"], medication_name="Drug C", start_date="2025-06-01"
    )

    response = api_client.get(MEDICATIONS_NESTED_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [
        newer_active["id"],  # active, newest first
        older_active["id"],  # active, older
        stopped["id"],  # stopped last — history is preserved
    ]


def test_list_filter_by_status_active(api_client):
    patient = _make_patient(api_client, "۸")
    _create_medication_record(api_client, patient["id"], medication_name="Drug D")
    _create_medication_record(
        api_client, patient["id"], medication_name="Drug E", status="stopped"
    )

    response = api_client.get(
        MEDICATIONS_NESTED_URL.format(patient_id=patient["id"]),
        params={"status": "active"},
    )

    items = response.json()
    assert len(items) == 1
    assert items[0]["medication"]["name"] == "Drug D"


def test_list_for_nonexistent_patient_returns_404(api_client):
    response = api_client.get(MEDICATIONS_NESTED_URL.format(patient_id=999999))

    assert response.status_code == 404


# --- get / patch / delete ---


def test_get_patient_medication_and_missing(api_client):
    patient = _make_patient(api_client, "۹")
    record = _create_medication_record(api_client, patient["id"])

    ok = api_client.get(PATIENT_MEDICATIONS_ITEM_URL.format(record_id=record["id"]))
    assert ok.status_code == 200
    assert ok.json() == record

    missing = api_client.get(PATIENT_MEDICATIONS_ITEM_URL.format(record_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == PATIENT_MEDICATION_NOT_FOUND_DETAIL


def test_patch_updates_dose_and_status_transitions(api_client):
    patient = _make_patient(api_client, "۱۰")
    record = _create_medication_record(api_client, patient["id"])
    url = PATIENT_MEDICATIONS_ITEM_URL.format(record_id=record["id"])

    # active → stopped (records history instead of deleting)
    stopped = api_client.patch(
        url,
        json={"status": "stopped", "dosage": "1000 mg", "end_date": "2026-02-01"},
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["dosage"] == "1000 mg"

    # stopped → completed also valid (no artificial transition rules)
    completed = api_client.patch(url, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    # invalid status value → 422
    invalid = api_client.patch(url, json={"status": "paused"})
    assert invalid.status_code == 422


def test_patch_keeps_stopped_record_in_history(api_client):
    patient = _make_patient(api_client, "۱۱")
    record = _create_medication_record(api_client, patient["id"])

    api_client.patch(
        PATIENT_MEDICATIONS_ITEM_URL.format(record_id=record["id"]),
        json={"status": "stopped"},
    )

    still_listed = api_client.get(
        MEDICATIONS_NESTED_URL.format(patient_id=patient["id"])
    )
    assert len(still_listed.json()) == 1
    assert still_listed.json()[0]["status"] == "stopped"


def test_patch_missing_record_returns_404(api_client):
    response = api_client.patch(
        PATIENT_MEDICATIONS_ITEM_URL.format(record_id=999999),
        json={"dosage": "10 mg"},
    )

    assert response.status_code == 404


def test_delete_patient_medication_returns_204_then_404(api_client):
    patient = _make_patient(api_client, "۱۲")
    record = _create_medication_record(api_client, patient["id"])
    url = PATIENT_MEDICATIONS_ITEM_URL.format(record_id=record["id"])

    assert api_client.delete(url).status_code == 204
    assert api_client.get(url).status_code == 404
