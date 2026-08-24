"""Condition API tests (require a running PostgreSQL)."""

from app.api.v1.routes.conditions import CONDITION_NOT_FOUND_DETAIL
from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL

PATIENTS_URL = "/api/v1/patients"
CONDITIONS_NESTED_URL = "/api/v1/patients/{patient_id}/conditions"
CONDITIONS_ITEM_URL = "/api/v1/conditions/{condition_id}"


def _make_patient(api_client) -> dict:
    response = api_client.post(
        PATIENTS_URL, json={"first_name": "آزمون", "last_name": "شرایط"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_condition(api_client, patient_id: int, **overrides) -> dict:
    payload = {"name": "دیابت نوع ۲ (Type 2 Diabetes)", "onset_date": "2024-05-01"}
    payload.update(overrides)
    response = api_client.post(CONDITIONS_NESTED_URL.format(patient_id=patient_id), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---


def test_create_condition(api_client):
    patient = _make_patient(api_client)

    condition = _create_condition(api_client, patient["id"])

    assert condition["id"] > 0
    assert condition["patient_id"] == patient["id"]
    assert condition["name"] == "دیابت نوع ۲ (Type 2 Diabetes)"
    assert condition["status"] == "active"  # default
    assert condition["created_at"] is not None


def test_create_condition_nonexistent_patient_returns_404(api_client):
    response = api_client.post(
        CONDITIONS_NESTED_URL.format(patient_id=999999), json={"name": "آسم"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


def test_create_condition_invalid_status_returns_422(api_client):
    patient = _make_patient(api_client)

    response = api_client.post(
        CONDITIONS_NESTED_URL.format(patient_id=patient["id"]),
        json={"name": "آسم", "status": "chronic"},  # not a valid enum value
    )

    assert response.status_code == 422


# --- list ---


def test_list_conditions_scoped_to_patient_and_ordered(api_client):
    patient = _make_patient(api_client)
    resolved = _create_condition(
        api_client, patient["id"], name="برونشیت حاد", status="resolved",
        onset_date="2020-01-01",
    )
    active = _create_condition(
        api_client, patient["id"], name="آسم", onset_date="2019-01-01"
    )
    other_patient = _make_patient(api_client)
    _create_condition(api_client, other_patient["id"], name="بیماری بیمار دیگر")

    response = api_client.get(CONDITIONS_NESTED_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [active["id"], resolved["id"]]  # active first
    assert len(items) == 2  # other patient's condition not included


# --- get / patch / delete ---


def test_get_condition_and_missing_condition(api_client):
    patient = _make_patient(api_client)
    condition = _create_condition(api_client, patient["id"])

    ok = api_client.get(CONDITIONS_ITEM_URL.format(condition_id=condition["id"]))
    assert ok.status_code == 200
    assert ok.json() == condition

    missing = api_client.get(CONDITIONS_ITEM_URL.format(condition_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == CONDITION_NOT_FOUND_DETAIL


def test_patch_condition_marks_resolved(api_client):
    patient = _make_patient(api_client)
    condition = _create_condition(api_client, patient["id"])

    response = api_client.patch(
        CONDITIONS_ITEM_URL.format(condition_id=condition["id"]),
        json={"status": "resolved", "resolved_date": "2026-01-10"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolved_date"] == "2026-01-10"
    assert body["name"] == condition["name"]  # untouched


def test_patch_missing_condition_returns_404(api_client):
    response = api_client.patch(
        CONDITIONS_ITEM_URL.format(condition_id=999999), json={"notes": "x"}
    )

    assert response.status_code == 404


def test_delete_condition_returns_204_then_404(api_client):
    patient = _make_patient(api_client)
    condition = _create_condition(api_client, patient["id"])
    url = CONDITIONS_ITEM_URL.format(condition_id=condition["id"])

    assert api_client.delete(url).status_code == 204
    assert api_client.get(url).status_code == 404
