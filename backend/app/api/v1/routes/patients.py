"""Patient endpoints (API v1) — CRUD plus the clinical overview."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    PATIENT_NOT_FOUND_DETAIL,
    get_current_user,
    patient_from_id,
)
from app.db.session import get_db
from app.models import (
    Allergy,
    ClinicalNote,
    Condition,
    LabResult,
    Patient,
    PatientMedication,
    PatientUserAccess,
    User,
)
from app.models.enums import (
    AllergySeverity,
    ConditionStatus,
    MedicationStatus,
    UserRole,
)
from app.schemas.allergy import AllergyResponse
from app.schemas.clinical_note import ClinicalNoteResponse
from app.schemas.condition import ConditionResponse
from app.schemas.lab_result import LabResultResponse
from app.schemas.medication import PatientMedicationResponse
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientOverviewResponse,
    PatientResponse,
    PatientUpdate,
)
from app.schemas.patient_context import (
    PatientContextResponse,
    PatientTimelineResponse,
)
from app.services.patient_context import build_patient_context, build_timeline

router = APIRouter(prefix="/patients", tags=["patients"])

DUPLICATE_NATIONAL_CODE_DETAIL = "این کد ملی قبلاً برای بیمار دیگری ثبت شده است."

RECENT_ITEMS_LIMIT = 5


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patient",
    responses={status.HTTP_409_CONFLICT: {"description": "کد ملی تکراری"}},
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Patient:
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
    # the creating doctor is granted access to their new patient
    # (admins already see everything)
    if user.role == UserRole.doctor:
        db.add(PatientUserAccess(patient_id=patient.id, user_id=user.id))
        db.commit()
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
    user: User = Depends(get_current_user),
) -> PatientListResponse:
    statement = select(Patient)
    if user.role == UserRole.doctor:
        # doctors see ONLY their explicitly assigned patients
        statement = statement.join(PatientUserAccess).where(
            PatientUserAccess.user_id == user.id
        )
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
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def get_patient(patient: Patient = Depends(patient_from_id)) -> Patient:
    return patient


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Partially update a patient",
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def update_patient(
    payload: PatientUpdate,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> Patient:
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
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def delete_patient(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> None:
    db.delete(patient)
    db.commit()


@router.get(
    "/{patient_id}/context",
    response_model=PatientContextResponse,
    summary="Get the complete structured patient context",
    description=(
        "Everything that exists in the database for this patient: "
        "demographics, conditions, medications (with history), allergies, "
        "lab values, documents (incl. extracted/OCR text), voice notes "
        "(incl. raw transcripts) and clinical notes. Pure structured data — "
        "no AI summary. This is the input layer for the future AI copilot."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def get_patient_context(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> PatientContextResponse:
    return build_patient_context(db, patient)


@router.get(
    "/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
    summary="Get the unified clinical timeline",
    description=(
        "Chronological timeline derived from the actual records: documents, "
        "lab results, clinical notes, voice notes, condition onsets/"
        "resolutions and medication starts/stops. Newest first; items "
        "without a primary date fall back to their record's created_at."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def get_patient_timeline(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> PatientTimelineResponse:
    items = build_timeline(db, patient)
    return PatientTimelineResponse(items=items, total=len(items))


@router.get(
    "/{patient_id}/overview",
    response_model=PatientOverviewResponse,
    summary="Get a structured clinical overview of a patient",
    description=(
        "Pure structured database data — no AI summary is generated. "
        "Conditions: active first. Medications: active only. Allergies: "
        "severe first. Labs/notes: the 5 most recent."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": PATIENT_NOT_FOUND_DETAIL}},
)
def get_patient_overview(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> PatientOverviewResponse:
    conditions = db.scalars(
        select(Condition)
        .where(Condition.patient_id == patient.id)
        .order_by(
            case((Condition.status == ConditionStatus.active, 0), else_=1),
            Condition.onset_date.desc().nullslast(),
            Condition.id.desc(),
        )
    ).all()

    active_medications = db.scalars(
        select(PatientMedication)
        .where(
            PatientMedication.patient_id == patient.id,
            PatientMedication.status == MedicationStatus.active,
        )
        .order_by(
            PatientMedication.start_date.desc().nullslast(),
            PatientMedication.id.desc(),
        )
    ).all()

    allergies = db.scalars(
        select(Allergy)
        .where(Allergy.patient_id == patient.id)
        .order_by(
            case(
                (Allergy.severity == AllergySeverity.severe, 0),
                (Allergy.severity == AllergySeverity.moderate, 1),
                (Allergy.severity == AllergySeverity.mild, 2),
                else_=3,
            ),
            Allergy.id.desc(),
        )
    ).all()

    recent_lab_results = db.scalars(
        select(LabResult)
        .where(LabResult.patient_id == patient.id)
        .order_by(LabResult.result_date.desc().nullslast(), LabResult.id.desc())
        .limit(RECENT_ITEMS_LIMIT)
    ).all()

    recent_clinical_notes = db.scalars(
        select(ClinicalNote)
        .where(ClinicalNote.patient_id == patient.id)
        .order_by(ClinicalNote.created_at.desc(), ClinicalNote.id.desc())
        .limit(RECENT_ITEMS_LIMIT)
    ).all()

    return PatientOverviewResponse(
        patient=patient,
        conditions=list(conditions),
        active_medications=list(active_medications),
        allergies=list(allergies),
        recent_lab_results=list(recent_lab_results),
        recent_clinical_notes=list(recent_clinical_notes),
    )
