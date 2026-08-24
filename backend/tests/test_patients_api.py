"""Patient CRUD API tests (require a running PostgreSQL)."""

PATIENTS_URL = "/api/v1/patients"


def _create_payload(**overrides) -> dict:
    payload = {
        "first_name": "زهرا",
        "last_name": "محمدی",
        "national_code": "0099999999",
        "date_of_birth": "1990-04-12",
        "gender": "female",
        "phone": "09129999999",
    }
    payload.update(overrides)
    return payload


def _create_patient(api_client, **overrides) -> dict:
    response = api_client.post(PATIENTS_URL, json=_create_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---


def test_create_patient_returns_201_and_body(api_client):
    body = _create_patient(api_client)

    assert body["id"] > 0
    assert body["first_name"] == "زهرا"
    assert body["national_code"] == "0099999999"
    assert body["gender"] == "female"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_patient_with_minimal_body(api_client):
    response = api_client.post(
        PATIENTS_URL, json={"first_name": "رضا", "last_name": "کریمی"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["national_code"] is None
    assert body["gender"] == "unknown"  # default


def test_create_rejects_invalid_national_code(api_client):
    response = api_client.post(
        PATIENTS_URL, json=_create_payload(national_code="12345")
    )

    assert response.status_code == 422


def test_create_rejects_missing_required_fields(api_client):
    response = api_client.post(PATIENTS_URL, json={"first_name": "تنها نام"})

    assert response.status_code == 422


def test_create_duplicate_national_code_returns_409(api_client):
    _create_patient(api_client)

    response = api_client.post(
        PATIENTS_URL,
        json=_create_payload(first_name="سعید", last_name="نجفی"),
    )

    assert response.status_code == 409
    assert "کد ملی" in response.json()["detail"]


# --- read ---


def test_get_patient_returns_body(api_client):
    created = _create_patient(api_client)

    response = api_client.get(f"{PATIENTS_URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_patient_returns_404(api_client):
    response = api_client.get(f"{PATIENTS_URL}/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "بیمار یافت نشد."


def test_list_patients_with_pagination(api_client):
    for index in range(3):
        _create_patient(
            api_client,
            national_code=f"11111111{index:02d}",
            last_name=f"محمدی {index + 1}",
        )

    page = api_client.get(PATIENTS_URL, params={"limit": 2, "offset": 0})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    page = api_client.get(PATIENTS_URL, params={"limit": 2, "offset": 2})
    assert len(page.json()["items"]) == 1


def test_list_patients_search_by_name(api_client):
    _create_patient(api_client, last_name="رضایی‌فر")
    _create_patient(
        api_client, first_name="مینا", last_name="احمدی", national_code="0088888888"
    )

    response = api_client.get(PATIENTS_URL, params={"q": "احمدی"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["first_name"] == "مینا"


# --- update ---


def test_update_patient_partial(api_client):
    created = _create_patient(api_client)

    response = api_client.patch(
        f"{PATIENTS_URL}/{created['id']}", json={"phone": "09121112233"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "09121112233"
    assert body["first_name"] == "زهرا"  # untouched
    assert body["national_code"] == "0099999999"  # untouched


def test_update_missing_patient_returns_404(api_client):
    response = api_client.patch(f"{PATIENTS_URL}/999999", json={"phone": "09120000000"})

    assert response.status_code == 404


def test_update_to_duplicate_national_code_returns_409(api_client):
    first = _create_patient(api_client)
    second = _create_patient(api_client, national_code="0077777777")

    response = api_client.patch(
        f"{PATIENTS_URL}/{second['id']}",
        json={"national_code": first["national_code"]},
    )

    assert response.status_code == 409


# --- delete ---


def test_delete_patient_returns_204_then_404(api_client):
    created = _create_patient(api_client)

    response = api_client.delete(f"{PATIENTS_URL}/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    response = api_client.get(f"{PATIENTS_URL}/{created['id']}")
    assert response.status_code == 404


def test_delete_missing_patient_returns_404(api_client):
    response = api_client.delete(f"{PATIENTS_URL}/999999")

    assert response.status_code == 404
