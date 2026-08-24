"""Patient CRUD endpoints (API v1)."""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.session import get_db
from app.models import Patient
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter(prefix="/patients", tags=["patients"])

DUPLICATE_NATIONAL_CODE_DETAIL = "این کد ملی قبلاً برای بیمار دیگری ثبت شده است."
PATIENT_NOT_FOUND_DETAIL = "بیمار یافت نشد."


def _get_patient_or_404(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PATIENT_NOT_FOUND_DETAIL
        )
    return patient


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patient",
)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> Patient:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_NATIONAL_CODE_DETAIL,
        ) from None
    db.refresh(patient)
    return patient


@router.get("", response_model=PatientListResponse, summary="List patients")
def list_patients(
    q: str | None = Query(
        default=None, description="جست‌وجو در نام، نام خانوادگی یا کد ملی"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PatientListResponse:
    statement = select(Patient)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.national_code.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    items = db.scalars(
        statement.order_by(Patient.id).offset(offset).limit(limit)
    ).all()
    return PatientListResponse(items=items, total=total or 0)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get a patient by id",
)
def get_patient(patient_id: int, db: Session = Depends(get_db)) -> Patient:
    return _get_patient_or_404(db, patient_id)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Partially update a patient",
)
def update_patient(
    patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db)
) -> Patient:
    patient = _get_patient_or_404(db, patient_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_NATIONAL_CODE_DETAIL,
        ) from None
    db.refresh(patient)
    return patient


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a patient (and all related clinical data)",
)
def delete_patient(patient_id: int, db: Session = Depends(get_db)) -> None:
    patient = _get_patient_or_404(db, patient_id)
    db.delete(patient)
    db.commit()
