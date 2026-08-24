"""Patient overview API tests (require a running PostgreSQL)."""

from datetime import date, datetime, timezone

from app.api.v1.dependencies import PATIENT_NOT_FOUND_DETAIL
from app.models import ClinicalNote, LabResult, Patient

PATIENTS_URL = "/api/v1/patients"
OVERVIEW_URL = "/api/v1/patients/{patient_id}/overview"


def _make_patient(api_client) -> dict:
    response = api_client.post(
        PATIENTS_URL,
        json={"first_name": "نگار", "last_name": "مروری"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_condition(api_client, patient_id: int, name: str, **overrides) -> dict:
    payload = {"name": name}
    payload.update(overrides)
    response = api_client.post(
        f"/api/v1/patients/{patient_id}/conditions", json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_medication(api_client, patient_id: int, name: str, **overrides) -> dict:
    payload = {"medication_name": name}
    payload.update(overrides)
    response = api_client.post(
        f"/api/v1/patients/{patient_id}/medications", json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_allergy(api_client, patient_id: int, allergen: str, **overrides) -> dict:
    payload = {"allergen": allergen}
    payload.update(overrides)
    response = api_client.post(f"/api/v1/patients/{patient_id}/allergies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _insert_lab(db_session, patient_id: int, test_name: str, day: int) -> None:
    db_session.add(
        LabResult(
            patient_id=patient_id,
            test_name=test_name,
            value="100",
            result_date=date(2026, 1, day),
        )
    )
    db_session.commit()


def _insert_note(db_session, patient_id: int, title: str) -> None:
    db_session.add(
        ClinicalNote(patient_id=patient_id, title=title, content="محتوای یادداشت")
    )
    db_session.commit()


def test_overview_contains_all_sections(api_client):
    patient = _make_patient(api_client)
    patient_id = patient["id"]
    _add_condition(api_client, patient_id, "دیابت نوع ۲")
    _add_condition(api_client, patient_id, "برونشیت", status="resolved")
    _add_medication(api_client, patient_id, "Metformin 500")
    _add_medication(api_client, patient_id, "Drug Old", status="stopped")
    _add_allergy(api_client, patient_id, "پنی‌سیلین", severity="severe")

    response = api_client.get(OVERVIEW_URL.format(patient_id=patient_id))

    assert response.status_code == 200
    overview = response.json()

    # patient profile
    assert overview["patient"]["id"] == patient_id
    assert overview["patient"]["first_name"] == "نگار"

    # conditions: active first
    assert [c["status"] for c in overview["conditions"]] == ["active", "resolved"]

    # medications: active only
    assert len(overview["active_medications"]) == 1
    assert overview["active_medications"][0]["medication"]["name"] == "Metformin 500"

    # allergies
    assert overview["allergies"][0]["allergen"] == "پنی‌سیلین"

    # labs/notes sections exist
    assert overview["recent_lab_results"] == []
    assert overview["recent_clinical_notes"] == []


def test_overview_recent_labs_limited_to_five_newest_first(api_client, db_session):
    patient = _make_patient(api_client)
    patient_id = patient["id"]
    for day in range(1, 8):  # 7 labs on consecutive days
        _insert_lab(db_session, patient_id, f"Lab {day}", day)

    response = api_client.get(OVERVIEW_URL.format(patient_id=patient_id))

    labs = response.json()["recent_lab_results"]
    assert len(labs) == 5
    assert [lab["result_date"] for lab in labs] == [
        "2026-01-07", "2026-01-06", "2026-01-05", "2026-01-04", "2026-01-03"
    ]


def test_overview_recent_notes_limited_to_five_newest_first(api_client, db_session):
    patient = _make_patient(api_client)
    patient_id = patient["id"]
    for index in range(7):
        _insert_note(db_session, patient_id, f"یادداشت {index + 1}")

    response = api_client.get(OVERVIEW_URL.format(patient_id=patient_id))

    notes = response.json()["recent_clinical_notes"]
    assert len(notes) == 5
    # newest first — the latest-created note comes first
    assert notes[0]["title"] == "یادداشت 7"
    assert notes[-1]["title"] == "یادداشت 3"


def test_overview_is_scoped_to_the_patient(api_client, db_session):
    patient = _make_patient(api_client)
    other = _make_patient(api_client)
    _add_condition(api_client, other["id"], "بیماری بیمار دیگر")
    _insert_lab(db_session, other["id"], "Lab Other", 1)

    response = api_client.get(OVERVIEW_URL.format(patient_id=patient["id"]))

    overview = response.json()
    assert overview["conditions"] == []
    assert overview["recent_lab_results"] == []


def test_overview_nonexistent_patient_returns_404(api_client):
    response = api_client.get(OVERVIEW_URL.format(patient_id=999999))

    assert response.status_code == 404
    assert response.json()["detail"] == PATIENT_NOT_FOUND_DETAIL
