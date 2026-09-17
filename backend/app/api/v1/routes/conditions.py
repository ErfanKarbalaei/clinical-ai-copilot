"""Condition endpoints (API v1) — nested under a patient, plus flat item routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    ensure_patient_access,
    get_current_user,
    patient_from_id,
)
from app.db.session import get_db
from app.models import Condition, Patient, User
from app.models.enums import ConditionStatus
from app.schemas.condition import ConditionCreate, ConditionResponse, ConditionUpdate

router = APIRouter(tags=["conditions"])

CONDITION_NOT_FOUND_DETAIL = "مشکل بالینی یافت نشد."

# Active conditions first, then newest onset first (deterministic ordering).
_condition_order = (
    case((Condition.status == ConditionStatus.active, 0), else_=1),
    Condition.onset_date.desc().nullslast(),
    Condition.id.desc(),
)


def _get_condition_or_404(
    db: Session, user: User, condition_id: int
) -> Condition:
    condition = db.get(Condition, condition_id)
    if condition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=CONDITION_NOT_FOUND_DETAIL
        )
    ensure_patient_access(db, user, condition.patient_id)
    return condition


@router.post(
    "/patients/{patient_id}/conditions",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a condition to a patient",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def create_condition(
    payload: ConditionCreate,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> Condition:
    condition = Condition(patient_id=patient.id, **payload.model_dump())
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return condition


@router.get(
    "/patients/{patient_id}/conditions",
    response_model=list[ConditionResponse],
    summary="List a patient's conditions",
    description="Active conditions first, then newest onset first.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_conditions(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[Condition]:
    conditions = db.scalars(
        select(Condition)
        .where(Condition.patient_id == patient.id)
        .order_by(*_condition_order)
    ).all()
    return list(conditions)


@router.get(
    "/conditions/{condition_id}",
    response_model=ConditionResponse,
    summary="Get a condition by id",
    responses={status.HTTP_404_NOT_FOUND: {"description": "مشکل بالینی یافت نشد"}},
)
def get_condition(
    condition_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Condition:
    return _get_condition_or_404(db, user, condition_id)


@router.patch(
    "/conditions/{condition_id}",
    response_model=ConditionResponse,
    summary="Partially update a condition",
    responses={status.HTTP_404_NOT_FOUND: {"description": "مشکل بالینی یافت نشد"}},
)
def update_condition(
    condition_id: int,
    payload: ConditionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Condition:
    condition = _get_condition_or_404(db, user, condition_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(condition, field, value)
    db.commit()
    db.refresh(condition)
    return condition


@router.delete(
    "/conditions/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a condition",
    responses={status.HTTP_404_NOT_FOUND: {"description": "مشکل بالینی یافت نشد"}},
)
def delete_condition(
    condition_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    condition = _get_condition_or_404(db, user, condition_id)
    db.delete(condition)
    db.commit()
