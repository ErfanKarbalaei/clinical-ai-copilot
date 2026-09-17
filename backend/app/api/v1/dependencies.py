"""Shared API dependencies for v1 routes.

Task 18 adds authentication + patient-level authorization on top of the
existing ``patient_from_id`` choke point: every nested patient route that
already depends on it now also requires a valid Bearer token AND explicit
patient access (admin bypasses). Flat child routes call
``ensure_patient_access`` after loading their child row, so a guessed id of
ANOTHER patient's child resource can never be used.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_db
from app.models import Patient, PatientUserAccess, User
from app.models.enums import UserRole

PATIENT_NOT_FOUND_DETAIL = "بیمار یافت نشد."
CREDENTIALS_INVALID_DETAIL = "احراز هویت لازم است یا توکن معتبر نیست."
PATIENT_ACCESS_DENIED_DETAIL = "شما به پروندهٔ این بیمار دسترسی ندارید."

# Swagger-friendly bearer extraction (tokenUrl points at the login route).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve the Bearer token → active user, or 401 (no detail leakage)."""
    user_id = security.decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_INVALID_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_INVALID_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def user_has_patient_access(db: Session, user: User, patient_id: int) -> bool:
    """Admins access everything; doctors only their explicitly assigned patients."""
    if user.role == UserRole.admin:
        return True
    return (
        db.scalar(
            select(PatientUserAccess.id).where(
                PatientUserAccess.patient_id == patient_id,
                PatientUserAccess.user_id == user.id,
            )
        )
        is not None
    )


def ensure_patient_access(db: Session, user: User, patient_id: int) -> None:
    """403 unless the user may access this patient (call after loading a child)."""
    if not user_has_patient_access(db, user, patient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PATIENT_ACCESS_DENIED_DETAIL,
        )


def patient_from_id(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Patient:
    """Resolve a patient from the path id (404) and enforce access (403)."""
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PATIENT_NOT_FOUND_DETAIL
        )
    ensure_patient_access(db, user, patient.id)
    return patient
