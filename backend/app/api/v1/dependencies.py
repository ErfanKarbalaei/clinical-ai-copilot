"""Shared API dependencies for v1 routes."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Patient

PATIENT_NOT_FOUND_DETAIL = "بیمار یافت نشد."


def patient_from_id(patient_id: int, db: Session = Depends(get_db)) -> Patient:
    """Resolve a patient from the path id or raise 404 (Persian message)."""
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PATIENT_NOT_FOUND_DETAIL
        )
    return patient
