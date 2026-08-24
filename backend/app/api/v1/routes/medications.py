"""Patient medication endpoints (API v1) — nested under a patient, plus flat item routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.dependencies import patient_from_id
from app.db.session import get_db
from app.models import Medication, Patient, PatientMedication
from app.models.enums import MedicationStatus
from app.schemas.medication import (
    PatientMedicationCreate,
    PatientMedicationResponse,
    PatientMedicationUpdate,
)
from app.services.medications import get_or_create_medication

router = APIRouter(tags=["medications"])

PATIENT_MEDICATION_NOT_FOUND_DETAIL = "داروی بیمار یافت نشد."
MEDICATION_NOT_FOUND_DETAIL = "دارو در فهرست داروها یافت نشد."

# Active first, then stopped, then completed; within a group the most
# recently started first (deterministic ordering for the clinical UI).
_medication_order = (
    case(
        (PatientMedication.status == MedicationStatus.active, 0),
        (PatientMedication.status == MedicationStatus.stopped, 1),
        else_=2,
    ),
    PatientMedication.start_date.desc().nullslast(),
    PatientMedication.id.desc(),
)


def _get_patient_medication_or_404(
    db: Session, patient_medication_id: int
) -> PatientMedication:
    record = db.scalars(
        select(PatientMedication)
        .where(PatientMedication.id == patient_medication_id)
        .options(selectinload(PatientMedication.medication))
    ).first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PATIENT_MEDICATION_NOT_FOUND_DETAIL,
        )
    return record


@router.post(
    "/patients/{patient_id}/medications",
    response_model=PatientMedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a medication to a patient",
    description=(
        "Reference the catalog by `medication_id`, or send `medication_name` "
        "(an existing catalog entry is reused, otherwise one is created)."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یا دارو یافت نشد"}
    },
)
def create_patient_medication(
    payload: PatientMedicationCreate,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> PatientMedication:
    if payload.medication_id is not None:
        medication = db.get(Medication, payload.medication_id)
        if medication is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MEDICATION_NOT_FOUND_DETAIL,
            )
    else:
        medication = get_or_create_medication(
            db, name=payload.medication_name or "", generic_name=payload.generic_name
        )

    record = PatientMedication(
        patient_id=patient.id,
        medication=medication,
        **payload.record_fields,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/patients/{patient_id}/medications",
    response_model=list[PatientMedicationResponse],
    summary="List a patient's medications",
    description=(
        "Active medications first, then stopped, then completed; within a "
        "group, most recently started first. Stopped history is kept — use "
        "`?status=` to filter (e.g. `?status=active` for current medications)."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_patient_medications(
    medication_status: MedicationStatus | None = Query(
        default=None, alias="status", description="فیلتر بر اساس وضعیت"
    ),
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[PatientMedication]:
    statement = (
        select(PatientMedication)
        .where(PatientMedication.patient_id == patient.id)
        .options(selectinload(PatientMedication.medication))
        .order_by(*_medication_order)
    )
    if medication_status is not None:
        statement = statement.where(PatientMedication.status == medication_status)
    records = db.scalars(statement).all()
    return list(records)


@router.get(
    "/patient-medications/{patient_medication_id}",
    response_model=PatientMedicationResponse,
    summary="Get a patient medication by id",
    responses={status.HTTP_404_NOT_FOUND: {"description": "داروی بیمار یافت نشد"}},
)
def get_patient_medication(
    patient_medication_id: int, db: Session = Depends(get_db)
) -> PatientMedication:
    return _get_patient_medication_or_404(db, patient_medication_id)


@router.patch(
    "/patient-medications/{patient_medication_id}",
    response_model=PatientMedicationResponse,
    summary="Partially update a patient medication",
    description=(
        "Stopping a medication does NOT delete it — history is preserved "
        "by design (send `{\"status\": \"stopped\"}`)."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "داروی بیمار یافت نشد"}},
)
def update_patient_medication(
    patient_medication_id: int,
    payload: PatientMedicationUpdate,
    db: Session = Depends(get_db),
) -> PatientMedication:
    record = _get_patient_medication_or_404(db, patient_medication_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete(
    "/patient-medications/{patient_medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a patient medication record",
    description=(
        "Prefer PATCH to `stopped` — physical delete removes the history "
        "entry permanently."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "داروی بیمار یافت نشد"}},
)
def delete_patient_medication(
    patient_medication_id: int, db: Session = Depends(get_db)
) -> None:
    record = _get_patient_medication_or_404(db, patient_medication_id)
    db.delete(record)
    db.commit()
