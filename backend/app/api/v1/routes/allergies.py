"""Allergy endpoints (API v1) — nested under a patient, plus flat item routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    ensure_patient_access,
    get_current_user,
    patient_from_id,
)
from app.db.session import get_db
from app.models import Allergy, Patient, User
from app.models.enums import AllergySeverity
from app.schemas.allergy import AllergyCreate, AllergyResponse, AllergyUpdate

router = APIRouter(tags=["allergies"])

ALLERGY_NOT_FOUND_DETAIL = "حساسیت یافت نشد."

# Severe allergies first (deterministic ordering).
_allergy_order = (
    case(
        (Allergy.severity == AllergySeverity.severe, 0),
        (Allergy.severity == AllergySeverity.moderate, 1),
        (Allergy.severity == AllergySeverity.mild, 2),
        else_=3,
    ),
    Allergy.id.desc(),
)


def _get_allergy_or_404(
    db: Session, user: User, allergy_id: int
) -> Allergy:
    allergy = db.get(Allergy, allergy_id)
    if allergy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ALLERGY_NOT_FOUND_DETAIL
        )
    ensure_patient_access(db, user, allergy.patient_id)
    return allergy


@router.post(
    "/patients/{patient_id}/allergies",
    response_model=AllergyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an allergy to a patient",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def create_allergy(
    payload: AllergyCreate,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> Allergy:
    allergy = Allergy(patient_id=patient.id, **payload.model_dump())
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.get(
    "/patients/{patient_id}/allergies",
    response_model=list[AllergyResponse],
    summary="List a patient's allergies",
    description="More severe allergies first.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_allergies(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[Allergy]:
    allergies = db.scalars(
        select(Allergy)
        .where(Allergy.patient_id == patient.id)
        .order_by(*_allergy_order)
    ).all()
    return list(allergies)


@router.get(
    "/allergies/{allergy_id}",
    response_model=AllergyResponse,
    summary="Get an allergy by id",
    responses={status.HTTP_404_NOT_FOUND: {"description": "حساسیت یافت نشد"}},
)
def get_allergy(
    allergy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Allergy:
    return _get_allergy_or_404(db, user, allergy_id)


@router.patch(
    "/allergies/{allergy_id}",
    response_model=AllergyResponse,
    summary="Partially update an allergy",
    responses={status.HTTP_404_NOT_FOUND: {"description": "حساسیت یافت نشد"}},
)
def update_allergy(
    allergy_id: int,
    payload: AllergyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Allergy:
    allergy = _get_allergy_or_404(db, user, allergy_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(allergy, field, value)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.delete(
    "/allergies/{allergy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an allergy",
    responses={status.HTTP_404_NOT_FOUND: {"description": "حساسیت یافت نشد"}},
)
def delete_allergy(
    allergy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    allergy = _get_allergy_or_404(db, user, allergy_id)
    db.delete(allergy)
    db.commit()
