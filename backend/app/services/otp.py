"""Phone OTP issuance/verification (Task 21) — decoupled from delivery.

Security properties (all tested):
- 6-digit OTP from a CSPRNG, stored ONLY as a SHA-256 hash
- 2-minute expiry; max 5 verification attempts per OTP
- rate limiting: max 3 OTP requests per phone per 10 minutes
- consumed on success (reuse is rejected), replaced by a new request
- OTP codes and phone numbers are never logged
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import OtpRequest

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 120
MAX_VERIFY_ATTEMPTS = 5
MAX_REQUESTS_PER_WINDOW = 3
REQUEST_WINDOW_MINUTES = 10


class OtpRateLimitedError(Exception):
    """Too many OTP requests for this phone — try again later."""


class OtpInvalidError(Exception):
    """Code is wrong, expired, exhausted, or unknown — same generic error."""


def _hash_code(phone_e164: str, code: str) -> str:
    """SHA-256 of phone+code — the plaintext OTP is never stored."""
    return hashlib.sha256(f"{phone_e164}:{code}".encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone(raw: str) -> str:
    """Normalize Iranian phone input to E.164 (+989xxxxxxxxx).

    Accepts 09123456789, 989123456789, +989123456789, 00989123456789.
    """
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:  # bare 9123456789
        digits = "0" + digits
    if not (digits.startswith("09") and len(digits) == 11):
        raise ValueError("invalid Iranian mobile number")
    return "+98" + digits[1:]


def issue_otp(db: Session, phone_e164: str) -> str:
    """Create a new OTP for the phone (replacing any previous one).

    Rate-limited per phone. Returns the PLAINTEXT code — the ONLY place it
    exists outside the delivery message; the caller must not log it.
    """
    window_start = _now() - timedelta(minutes=REQUEST_WINDOW_MINUTES)
    recent = db.scalars(
        select(OtpRequest)
        .where(OtpRequest.phone == phone_e164)
        .order_by(OtpRequest.id.desc())
        .limit(MAX_REQUESTS_PER_WINDOW)
    ).all()
    if (
        len(recent) >= MAX_REQUESTS_PER_WINDOW
        and recent[0].created_at >= window_start
    ):
        raise OtpRateLimitedError()

    code = f"{secrets.randbelow(1_000_000):06d}"
    otp = OtpRequest(
        phone=phone_e164,
        code_hash=_hash_code(phone_e164, code),
        expires_at=_now() + timedelta(seconds=OTP_TTL_SECONDS),
        attempts_left=MAX_VERIFY_ATTEMPTS,
    )
    db.add(otp)
    db.commit()
    logger.info(
        "otp issued (otp_id=%s, ttl=%ds) — code/phone never logged",
        otp.id, OTP_TTL_SECONDS,
    )
    return code


def verify_otp(db: Session, phone_e164: str, code: str) -> OtpRequest:
    """Verify and consume the newest OTP for the phone, or raise OtpInvalidError."""
    otp = db.scalars(
        select(OtpRequest)
        .where(OtpRequest.phone == phone_e164)
        .order_by(OtpRequest.id.desc())
        .limit(1)
    ).first()

    if (
        otp is None
        or otp.consumed_at is not None
        or otp.expires_at < _now()
        or otp.attempts_left <= 0
    ):
        raise OtpInvalidError()

    otp.attempts_left -= 1
    if not hmac.compare_digest(otp.code_hash, _hash_code(phone_e164, code)):
        db.commit()
        raise OtpInvalidError()

    otp.consumed_at = _now()
    db.commit()
    logger.info("otp verified and consumed (otp_id=%s)", otp.id)
    return otp
