"""Phone OTP login endpoints (Task 21) — Uniom/Soroush Plus delivery.

Flow: POST /auth/request-otp (phone) → hashed 6-digit OTP, delivered as a
Soroush Plus message through the Uniom REST API → POST /auth/verify-otp
(phone + code) → find-or-create user → the SAME JWT session as password
login. Existing password auth is untouched.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.auth import TokenResponse, UserResponse
from app.services.messaging import uniom
from app.services.messaging.uniom import (
    UniomError,
    UniomNotConfiguredError,
)
from app.services import otp as otp_service
from app.services.otp import OtpInvalidError, OtpRateLimitedError

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

MESSAGING_NOT_CONFIGURED_DETAIL = (
    "ارسال کد یک‌بارمصرف فعال نیست (UNIOM_API_KEY تنظیم نشده است)."
)
MESSAGING_FAILED_DETAIL = "ارسال کد انجام نشد؛ کمی بعد دوباره تلاش کنید."
RATE_LIMITED_DETAIL = "تعداد درخواست کد بیش از حد مجاز است؛ چند دقیقه دیگر تلاش کنید."
INVALID_OTP_DETAIL = "کد واردشده نامعتبر یا منقضی شده است."

OTP_MESSAGE_TEMPLATE = "کد ورود شما به Clinical AI Copilot:\n{code}\n(۲ دقیقه اعتبار دارد)"


class OtpRequestPayload(BaseModel):
    phone: str = Field(
        min_length=10, max_length=20, description="شمارهٔ موبایل (مثل 09123456789)"
    )


class OtpVerifyPayload(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    code: str = Field(min_length=6, max_length=6)


@router.post(
    "/request-otp",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a login OTP (delivered via Soroush Plus / Uniom)",
    description=(
        "Sends a 6-digit code to the phone via the linked Soroush Plus "
        "account. Rate-limited to 3 requests per phone per 10 minutes. "
        "The response is always generic (no user-existence oracle)."
    ),
    responses={
        status.HTTP_202_ACCEPTED: {"description": "کد ارسال شد (یا شمارهٔ ناشناخته — پاسخ یکسان)"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "شمارهٔ موبایل نامعتبر"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": RATE_LIMITED_DETAIL},
        status.HTTP_502_BAD_GATEWAY: {"description": MESSAGING_FAILED_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": MESSAGING_NOT_CONFIGURED_DETAIL},
    },
)
def request_otp(
    payload: OtpRequestPayload, db: Session = Depends(get_db)
) -> dict:
    try:
        phone_e164 = otp_service.normalize_phone(payload.phone)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="شمارهٔ موبایل معتبر نیست (مثال: 09123456789)",
        )

    try:
        code = otp_service.issue_otp(db, phone_e164)
    except OtpRateLimitedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMITED_DETAIL,
        ) from None

    try:
        uniom.get_service().send_message(
            phone_e164, OTP_MESSAGE_TEMPLATE.format(code=code)
        )
    except UniomNotConfiguredError:
        # the OTP row exists but cannot be delivered — remove it so the
        # user is not silently rate-limited by undeliverable codes
        from sqlalchemy import delete as sa_delete
        latest_id = db.scalar(
            select(otp_service.OtpRequest.id)
            .where(otp_service.OtpRequest.phone == phone_e164)
            .order_by(otp_service.OtpRequest.id.desc())
            .limit(1)
        )
        if latest_id is not None:
            db.execute(
                sa_delete(otp_service.OtpRequest).where(
                    otp_service.OtpRequest.id == latest_id
                )
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MESSAGING_NOT_CONFIGURED_DETAIL,
        ) from None
    except UniomError as error:
        logger.error("otp delivery failed (phone=%r): %s", phone_e164, error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=MESSAGING_FAILED_DETAIL,
        ) from None

    # generic response — never reveals whether the phone belongs to a user
    return {"detail": "در صورت معتبر بودن شماره، کد ورود ارسال شد."}


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify the OTP and log in (same JWT as password login)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": INVALID_OTP_DETAIL},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "ورودی نامعتبر"},
    },
)
def verify_otp(payload: OtpVerifyPayload, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        phone_e164 = otp_service.normalize_phone(payload.phone)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="شمارهٔ موبایل معتبر نیست",
        )

    try:
        otp_service.verify_otp(db, phone_e164, payload.code.strip())
    except OtpInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_OTP_DETAIL,
        ) from None

    user = db.scalar(select(User).where(User.phone == phone_e164))
    if user is None:
        # first login via OTP → create an inactive-password doctor account
        user = User(
            email=f"otp-{phone_e164[1:]}@example.com",
            phone=phone_e164,
            password_hash=None,
            full_name="کاربر پیامکی",
            role=UserRole.doctor,
        )
        db.add(user)
        db.commit()
        logger.info("otp-first-login user created (user_id=%s)", user.id)
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_OTP_DETAIL,  # generic — no account-status oracle
        )

    return TokenResponse(access_token=create_access_token(user))
