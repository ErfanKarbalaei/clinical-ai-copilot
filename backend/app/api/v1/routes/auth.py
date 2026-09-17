"""Authentication endpoints (API v1) — Task 18.

Development/MVP-friendly: open registration always creates a ``doctor``
(admin self-registration is rejected — admins come from the seed script);
login returns a JWT bearer token. Error messages never reveal whether the
email or the password was wrong, and password hashes never leave the
server.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core import security
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

EMAIL_ALREADY_REGISTERED_DETAIL = "این ایمیل قبلاً ثبت شده است."
INVALID_CREDENTIALS_DETAIL = "ایمیل یا گذرواژه درست نیست."
ADMIN_SELF_REGISTRATION_DETAIL = (
    "نقش ادمین از طریق ثبت‌نام قابل ایجاد نیست؛ فقط اسکریپت توسعه (seed)."
)
INACTIVE_ACCOUNT_DETAIL = "این حساب کاربری غیرفعال است."


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user (development-friendly; role is always doctor)",
    responses={
        status.HTTP_409_CONFLICT: {"description": EMAIL_ALREADY_REGISTERED_DETAIL},
        status.HTTP_403_FORBIDDEN: {"description": ADMIN_SELF_REGISTRATION_DETAIL},
    },
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    if payload.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_SELF_REGISTRATION_DETAIL,
        )
    user = User(
        email=payload.email.lower(),
        password_hash=security.hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=UserRole.doctor,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=EMAIL_ALREADY_REGISTERED_DETAIL,
        ) from None
    db.refresh(user)
    logger.info("user registered (id=%s, role=%s)", user.id, user.role)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email + password → JWT access token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": INVALID_CREDENTIALS_DETAIL}
    },
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    # same generic message for unknown email AND wrong password
    if user is None or not security.verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INACTIVE_ACCOUNT_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=security.create_access_token(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current authenticated user",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "احراز هویت لازم است"}},
)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
