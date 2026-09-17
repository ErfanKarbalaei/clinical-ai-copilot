"""Password hashing and JWT access tokens (Task 18).

Isolated and testable on purpose: bcrypt for passwords (never plaintext,
never logged, never returned) and PyJWT HS256 access tokens whose secret
and lifetime come from configuration (never hard-coded production
secrets — see JWT_SECRET_KEY in .env.example).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.models import User


def hash_password(plain: str) -> str:
    """bcrypt hash (UTF-8 encoded) for storage — never store plaintext."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    """Constant-time bcrypt verification against a stored hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User, *, expires_minutes: int | None = None) -> str:
    """Sign a JWT identifying the user (``sub`` = user id)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.JWT_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": str(user.id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Decode and validate a token → user id, or None when invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
