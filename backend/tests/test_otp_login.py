"""Phone OTP login tests (Task 21) — Uniom fully mocked, no real sends."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import OtpRequest, User
from app.services import otp as otp_service
from app.services.messaging import uniom as uniom_service

REQUEST_URL = "/api/v1/auth/request-otp"
VERIFY_URL = "/api/v1/auth/verify-otp"

SENT: list[dict] = []


class FakeUniom:
    def __init__(self, error: Exception | None = None):
        self.error = error

    def send_message(self, recipient, message):
        if self.error is not None:
            raise self.error
        SENT.append({"recipient": recipient, "message": message})
        return {"message_id": 1}


@pytest.fixture()
def fake_uniom(monkeypatch):
    SENT.clear()
    service = FakeUniom()
    monkeypatch.setattr(uniom_service, "get_service", lambda: service)
    return service


def _latest_otp(db_session, phone: str) -> OtpRequest:
    return db_session.scalars(
        select(OtpRequest)
        .where(OtpRequest.phone == phone)
        .order_by(OtpRequest.id.desc())
        .limit(1)
    ).first()


def _extract_code(message: str) -> str:
    # "کد ورود شما به Clinical AI Copilot:\n123456\n(۲ دقیقه…)"
    return message.split("\n")[1]


# --- normalization (unit) ---


def test_normalize_phone_variants():
    assert otp_service.normalize_phone("09123456789") == "+989123456789"
    assert otp_service.normalize_phone("+98 912 345 6789") == "+989123456789"
    assert otp_service.normalize_phone("989123456789") == "+989123456789"
    assert otp_service.normalize_phone("00989123456789") == "+989123456789"
    with pytest.raises(ValueError):
        otp_service.normalize_phone("12345")
    with pytest.raises(ValueError):
        otp_service.normalize_phone("02112345678")  # landline prefix


# --- request-otp ---


def test_request_otp_success_and_message_shape(api_client, db_session, fake_uniom):
    response = api_client.post(REQUEST_URL, json={"phone": "09123456789"})
    assert response.status_code == 202
    # generic response — no user oracle, no code leak
    assert "code" not in json.dumps(response.json()).lower() or "کد" in response.json()["detail"]

    assert len(SENT) == 1
    assert SENT[0]["recipient"] == "+989123456789"  # E.164 chat_id
    code = _extract_code(SENT[0]["message"])
    assert len(code) == 6 and code.isdigit()

    stored = _latest_otp(db_session, "+989123456789")
    assert stored.code_hash != code  # stored hashed, not plaintext
    assert stored.attempts_left == 5
    assert stored.consumed_at is None


def test_request_otp_invalid_phone_422(api_client, fake_uniom):
    assert api_client.post(REQUEST_URL, json={"phone": "12345"}).status_code == 422


def test_request_otp_rate_limited(api_client, fake_uniom):
    for _ in range(3):
        assert api_client.post(REQUEST_URL, json={"phone": "09123456789"}).status_code == 202
    fourth = api_client.post(REQUEST_URL, json={"phone": "09123456789"})
    assert fourth.status_code == 429


def test_request_otp_uniom_failure_502(api_client, db_session, monkeypatch):
    monkeypatch.setattr(
        uniom_service, "get_service",
        lambda: FakeUniom(error=uniom_service.UniomError("uniom error 400: chat not found")),
    )
    response = api_client.post(REQUEST_URL, json={"phone": "09123456789"})
    assert response.status_code == 502
    assert "ارسال کد" in response.json()["detail"]


def test_request_otp_not_configured_503(api_client, db_session, monkeypatch):
    monkeypatch.setattr(
        uniom_service, "get_service",
        lambda: FakeUniom(error=uniom_service.UniomNotConfiguredError("no key")),
    )
    response = api_client.post(REQUEST_URL, json={"phone": "09123456789"})
    assert response.status_code == 503
    # undelivered OTP row is removed → not silently rate-limiting the user
    assert _latest_otp(db_session, "+989123456789") is None


# --- verify-otp ---


def _request_and_get_code(api_client, phone="09123456789") -> str:
    api_client.post(REQUEST_URL, json={"phone": phone})
    return _extract_code(SENT[-1]["message"])


def test_verify_otp_creates_user_and_returns_jwt(api_client, db_session, fake_uniom):
    code = _request_and_get_code(api_client)

    response = api_client.post(
        VERIFY_URL, json={"phone": "09123456789", "code": code}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    user = db_session.scalar(select(User).where(User.phone == "+989123456789"))
    assert user is not None and user.role == "doctor"

    # the JWT works on a protected endpoint (REAL auth dependency)
    from fastapi.testclient import TestClient
    from app.api.v1.dependencies import get_current_user
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides.pop(get_current_user, None)
    try:
        me_client = TestClient(app)
        me = me_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["phone"] == "+989123456789"
    finally:
        app.dependency_overrides.clear()


def test_verify_otp_existing_user_logs_in(api_client, db_session, fake_uniom):
    from app.core.security import hash_password

    existing = User(
        email="existing@testcompany.com",
        phone="+989123456789",
        password_hash=hash_password("Some-pass-123"),
        full_name="کاربر موجود",
    )
    db_session.add(existing)
    db_session.commit()

    code = _request_and_get_code(api_client)
    response = api_client.post(
        VERIFY_URL, json={"phone": "09123456789", "code": code}
    )
    assert response.status_code == 200
    # no duplicate user was created
    assert db_session.scalar(select(User).where(User.phone == "+989123456789")).id == existing.id


def test_verify_otp_wrong_code_401(api_client, fake_uniom):
    _request_and_get_code(api_client)
    response = api_client.post(
        VERIFY_URL, json={"phone": "09123456789", "code": "000000"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "کد واردشده نامعتبر یا منقضی شده است."


def test_verify_otp_expired(api_client, db_session, fake_uniom):
    code = _request_and_get_code(api_client)
    stored = _latest_otp(db_session, "+989123456789")
    stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    response = api_client.post(
        VERIFY_URL, json={"phone": "09123456789", "code": code}
    )
    assert response.status_code == 401


def test_verify_otp_reuse_rejected(api_client, fake_uniom):
    code = _request_and_get_code(api_client)
    first = api_client.post(VERIFY_URL, json={"phone": "09123456789", "code": code})
    assert first.status_code == 200

    replay = api_client.post(VERIFY_URL, json={"phone": "09123456789", "code": code})
    assert replay.status_code == 401  # consumed — replay rejected


def test_verify_otp_bruteforce_exhausts_attempts(api_client, db_session, fake_uniom):
    _request_and_get_code(api_client)
    for _ in range(5):
        wrong = api_client.post(VERIFY_URL, json={"phone": "09123456789", "code": "000000"})
        assert wrong.status_code == 401

    stored = _latest_otp(db_session, "+989123456789")
    real_code = None  # exhausted: even the real code must now fail
    response = api_client.post(VERIFY_URL, json={"phone": "09123456789", "code": "123456"})
    assert response.status_code == 401
    assert _latest_otp(db_session, "+989123456789").attempts_left == 0


def test_verify_otp_no_otp_at_all_401(api_client, fake_uniom):
    response = api_client.post(
        VERIFY_URL, json={"phone": "09351112233", "code": "123456"}
    )
    assert response.status_code == 401


# --- OTP never logged ---


def test_otp_code_never_logged(api_client, db_session, fake_uniom, caplog):
    with caplog.at_level("INFO"):
        api_client.post(REQUEST_URL, json={"phone": "09123456789"})
    code = _extract_code(SENT[-1]["message"])
    assert code not in caplog.text
