"""Allergy API tests (require a running PostgreSQL)."""

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.api.v1.routes.allergies import ALLERGY_NOT_FOUND_DETAIL

PATIENTS_URL = "/api/v1/patients"
ALLERGIES_NESTED_URL = "/api/v1/patients/{patient_id}/allergies"
ALLERGIES_ITEM_URL = "/api/v1/allergies/{allergy_id}"


def _make_patient(api_client) -> dict:
    response = api_client.post(
        PATIENTS_URL, json={"first_name": "آزمون", "last_name": "حساسیت"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_allergy(api_client, patient_id: int, **overrides) -> dict:
    payload = {"allergen": "پنی‌سیلین (Penicillin)", "reaction": "کهیر"}
    payload.update(overrides)
    response = api_client.post(ALLERGIES_NESTED_URL.format(patient_id=patient_id), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---


def test_create_allergy(api_client):
    patient = _make_patient(api_client)

    allergy = _create_allergy(api_client, patient["id"], severity="severe")

    assert allergy["id"] > 0
    assert allergy["patient_id"] == patient["id"]
    assert allergy["allergen"] == "پنی‌سیلین (Penicillin)"
    assert allergy["severity"] == "severe"
    assert allergy["created_at"] is not None


def test_create_allergy_defaults_severity_to_unknown(api_client):
    patient = _make_patient(api_client)

    allergy = _create_allergy(api_client, patient["id"])

    assert allergy["severity"] == "unknown"


def test_create_allergy_nonexistent_patient_returns_404(api_client):
    response = api_client.post(
        ALLERGIES_NESTED_URL.format(patient_id=999999), json={"allergen": "گرد و غبار"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL


def test_create_allergy_invalid_severity_returns_422(api_client):
    patient = _make_patient(api_client)

    response = api_client.post(
        ALLERGIES_NESTED_URL.format(patient_id=patient["id"]),
        json={"allergen": "گرد و غبار", "severity": "fatal"},  # invalid enum
    )

    assert response.status_code == 422


# --- list ---


def test_list_allergies_severe_first_and_scoped(api_client):
    patient = _make_patient(api_client)
    mild = _create_allergy(api_client, patient["id"], allergen="گرده گل", severity="mild")
    severe = _create_allergy(
        api_client, patient["id"], allergen="آسپرین (Aspirin)", severity="severe"
    )
    other_patient = _make_patient(api_client)
    _create_allergy(api_client, other_patient["id"], allergen="پنیر")

    response = api_client.get(ALLERGIES_NESTED_URL.format(patient_id=patient["id"]))

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [severe["id"], mild["id"]]
    assert len(items) == 1 + 1  # other patient's allergy not included


# --- get / patch / delete ---


def test_get_allergy_and_missing_allergy(api_client):
    patient = _make_patient(api_client)
    allergy = _create_allergy(api_client, patient["id"])

    ok = api_client.get(ALLERGIES_ITEM_URL.format(allergy_id=allergy["id"]))
    assert ok.status_code == 200
    assert ok.json() == allergy

    missing = api_client.get(ALLERGIES_ITEM_URL.format(allergy_id=999999))
    assert missing.status_code == 404
    assert missing.json()["detail"] == ALLERGY_NOT_FOUND_DETAIL


def test_patch_allergy_updates_severity(api_client):
    patient = _make_patient(api_client)
    allergy = _create_allergy(api_client, patient["id"])

    response = api_client.patch(
        ALLERGIES_ITEM_URL.format(allergy_id=allergy["id"]),
        json={"severity": "moderate", "reaction": "تنگی نفس"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "moderate"
    assert body["reaction"] == "تنگی نفس"
    assert body["allergen"] == allergy["allergen"]  # untouched


def test_patch_missing_allergy_returns_404(api_client):
    response = api_client.patch(
        ALLERGIES_ITEM_URL.format(allergy_id=999999), json={"severity": "mild"}
    )

    assert response.status_code == 404


def test_delete_allergy_returns_204_then_404(api_client):
    patient = _make_patient(api_client)
    allergy = _create_allergy(api_client, patient["id"])
    url = ALLERGIES_ITEM_URL.format(allergy_id=allergy["id"])

    assert api_client.delete(url).status_code == 204
    assert api_client.get(url).status_code == 404
