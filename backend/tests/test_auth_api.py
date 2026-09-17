"""Authentication API tests (Task 18) — real auth dependency, no overrides."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.v1.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.main import app
from app.models import User
from app.models.enums import UserRole

AUTH_URL = "/api/v1/auth"
PATIENTS_URL = "/api/v1/patients"


@pytest.fixture()
def auth_client(db_session):
    """TestClient with the REAL auth dependency (only DB overridden)."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _register(client, email="user@testcompany.com", password="StrongPass123", **extra):
    return client.post(
        f"{AUTH_URL}/register",
        json={
            "email": email,
            "password": password,
            "full_name": "آزمون کاربر",
            **extra,
        },
    )


def _login(client, email="user@testcompany.com", password="StrongPass123"):
    return client.post(
        f"{AUTH_URL}/login", json={"email": email, "password": password}
    )


def _token_headers(client, email="user@testcompany.com", password="StrongPass123"):
    response = _login(client, email, password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- password hashing (unit) ---


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("Secret-123")
    assert hashed != "Secret-123"
    assert hashed.startswith("$2")  # bcrypt
    assert verify_password("Secret-123", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_garbage_hash_is_false():
    assert not verify_password("x", "not-a-real-hash")


def test_token_roundtrip(db_session):
    user = User(email="t@testcompany.com", password_hash="x", full_name="T")
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user)
    assert decode_access_token(token) == user.id


# --- registration ---


def test_register_success(auth_client, db_session):
    response = _register(auth_client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "user@testcompany.com"
    assert body["role"] == "doctor"
    assert "password_hash" not in body and "password" not in body

    stored = db_session.scalar(select(User).where(User.email == "user@testcompany.com"))
    assert stored.password_hash != "StrongPass123"  # never plaintext
    assert verify_password("StrongPass123", stored.password_hash)


def test_register_duplicate_email(auth_client):
    assert _register(auth_client).status_code == 201
    assert _register(auth_client).status_code == 409


def test_register_admin_role_rejected(auth_client):
    response = _register(auth_client, email="a@testcompany.com", role="admin")
    assert response.status_code == 403


# --- login ---


def test_login_success_returns_bearer_token(auth_client):
    _register(auth_client)
    response = _login(auth_client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_generic_401(auth_client):
    _register(auth_client)
    wrong = _login(auth_client, password="WrongPass123")
    unknown = _login(auth_client, email="ghost@testcompany.com")
    assert wrong.status_code == unknown.status_code == 401
    # identical message — no oracle about which part was wrong
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_login_inactive_user_401(auth_client, db_session):
    _register(auth_client, email="off@testcompany.com")
    user = db_session.scalar(select(User).where(User.email == "off@testcompany.com"))
    user.is_active = False
    db_session.commit()
    assert _login(auth_client, "off@testcompany.com").status_code == 401


# --- /auth/me + token validation ---


def test_me_returns_user_without_hash(auth_client):
    _register(auth_client)
    response = auth_client.get(f"{AUTH_URL}/me", headers=_token_headers(auth_client))
    assert response.status_code == 200
    assert response.json()["email"] == "user@testcompany.com"
    assert "password_hash" not in response.json()


def test_me_without_token_401(auth_client):
    assert auth_client.get(f"{AUTH_URL}/me").status_code == 401


def test_invalid_jwt_401(auth_client):
    headers = {"Authorization": "Bearer not-a-jwt"}
    assert auth_client.get(f"{AUTH_URL}/me", headers=headers).status_code == 401


def test_expired_jwt_401(auth_client, db_session):
    user = User(email="exp@testcompany.com", password_hash="x", full_name="E")
    db_session.add(user)
    db_session.commit()
    expired = create_access_token(user, expires_minutes=-10)
    response = auth_client.get(
        f"{AUTH_URL}/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_token_of_inactive_user_401(auth_client, db_session):
    _register(auth_client, email="off2@testcompany.com")
    user = db_session.scalar(select(User).where(User.email == "off2@testcompany.com"))
    token = create_access_token(user)
    user.is_active = False
    db_session.commit()
    response = auth_client.get(
        f"{AUTH_URL}/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


# --- protected endpoints require auth ---


def test_patients_list_requires_token(auth_client):
    assert auth_client.get(PATIENTS_URL).status_code == 401


def test_patient_detail_requires_token(auth_client, db_session):
    from app.models import Patient

    db_session.add(Patient(first_name="بیمار", last_name="راستی"))
    db_session.commit()
    patient_id = db_session.scalar(
        select(Patient.id).order_by(Patient.id.desc())
    )
    assert (
        auth_client.get(f"{PATIENTS_URL}/{patient_id}").status_code == 401
    )


def test_health_stays_public(client):
    assert client.get("/health").status_code == 200
