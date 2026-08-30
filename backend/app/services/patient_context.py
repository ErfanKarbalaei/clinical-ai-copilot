"""Patient context builder and unified clinical timeline.

Pure database reads — no AI, no LLM, no vector search. Everything is
gathered live from the existing tables so derived data can never drift
from the source of truth.

The context feeds the future AI clinical copilot; the timeline derives a
unified chronological view from the actual records (documents, lab results,
notes, voice notes, conditions, medications) rather than relying solely on
the `clinical_events` table, which only covers some record types.
"""

from datetime import date, datetime, time, timezone

from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Allergy,
    ClinicalNote,
    Condition,
    Document,
    LabResult,
    Patient,
    PatientMedication,
    VoiceNote,
)
from app.models.enums import (
    AllergySeverity,
    ConditionStatus,
    MedicationStatus,
)
from app.schemas.patient_context import PatientContextResponse, TimelineItem

_RECENT_LIMIT = 200  # defensive cap per section, far above realistic MVP use


def _as_utc_datetime(value: datetime | date | None, fallback: datetime) -> datetime:
    """Normalize a date/datetime for sorting; missing → fallback (created_at).

    Dates become midnight UTC; tz-naive datetimes are assumed UTC — created_at
    from PostgreSQL is tz-aware, this only guards hand-inserted rows.
    """
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def build_patient_context(db: Session, patient: Patient) -> PatientContextResponse:
    """Gather the patient's existing information from every relevant source."""

    conditions = db.scalars(
        select(Condition)
        .where(Condition.patient_id == patient.id)
        .order_by(
            case((Condition.status == ConditionStatus.active, 0), else_=1),
            Condition.onset_date.desc().nullslast(),
            Condition.id.desc(),
        )
        .limit(_RECENT_LIMIT)
    ).all()

    medications = db.scalars(
        select(PatientMedication)
        .where(PatientMedication.patient_id == patient.id)
        .options(selectinload(PatientMedication.medication))
        .order_by(
            case(
                (PatientMedication.status == MedicationStatus.active, 0),
                (PatientMedication.status == MedicationStatus.stopped, 1),
                else_=2,
            ),
            PatientMedication.start_date.desc().nullslast(),
            PatientMedication.id.desc(),
        )
        .limit(_RECENT_LIMIT)
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
        .limit(_RECENT_LIMIT)
    ).all()

    lab_results = db.scalars(
        select(LabResult)
        .where(LabResult.patient_id == patient.id)
        .order_by(LabResult.result_date.desc().nullslast(), LabResult.id.desc())
        .limit(_RECENT_LIMIT)
    ).all()

    documents = db.scalars(
        select(Document)
        .where(Document.patient_id == patient.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(_RECENT_LIMIT)
    ).all()

    voice_notes = db.scalars(
        select(VoiceNote)
        .where(VoiceNote.patient_id == patient.id)
        .order_by(VoiceNote.created_at.desc(), VoiceNote.id.desc())
        .limit(_RECENT_LIMIT)
    ).all()

    clinical_notes = db.scalars(
        select(ClinicalNote)
        .where(ClinicalNote.patient_id == patient.id)
        .order_by(ClinicalNote.created_at.desc(), ClinicalNote.id.desc())
        .limit(_RECENT_LIMIT)
    ).all()

    return PatientContextResponse(
        patient=patient,
        conditions=list(conditions),
        medications=list(medications),
        allergies=list(allergies),
        lab_results=list(lab_results),
        documents=list(documents),
        voice_notes=list(voice_notes),
        clinical_notes=list(clinical_notes),
        generated_at=datetime.now(timezone.utc),
    )


def build_timeline(db: Session, patient: Patient) -> list[TimelineItem]:
    """Unified chronological timeline derived from the actual records.

    Newest first. Missing primary dates fall back to the row's created_at
    so no event is ever dropped for lacking a date. Uses the same
    event_type/source_type vocabulary as the clinical_events table.
    """
    items: list[TimelineItem] = []

    def add(
        *,
        event_type: str,
        when: datetime | date | None,
        fallback: datetime,
        title: str,
        description: str | None,
        source_type: str,
        source_id: int,
    ) -> None:
        items.append(
            TimelineItem(
                event_type=event_type,
                date=_as_utc_datetime(when, fallback),
                title=title,
                description=description,
                source_type=source_type,
                source_id=source_id,
            )
        )

    for condition in db.scalars(
        select(Condition).where(Condition.patient_id == patient.id)
    ):
        add(
            event_type="condition_onset",
            when=condition.onset_date,
            fallback=condition.created_at,
            title=f"تشخیص: {condition.name}",
            description=condition.notes,
            source_type="condition",
            source_id=condition.id,
        )
        if condition.resolved_date is not None:
            add(
                event_type="condition_resolved",
                when=condition.resolved_date,
                fallback=condition.created_at,
                title=f"رفع: {condition.name}",
                description=None,
                source_type="condition",
                source_id=condition.id,
            )

    for record in db.scalars(
        select(PatientMedication)
        .where(PatientMedication.patient_id == patient.id)
        .options(selectinload(PatientMedication.medication))
    ):
        name = record.medication.name
        add(
            event_type="medication_started",
            when=record.start_date,
            fallback=record.created_at,
            title=f"شروع دارو: {name}",
            description=record.dosage,
            source_type="patient_medication",
            source_id=record.id,
        )
        if record.end_date is not None and record.status != MedicationStatus.active:
            add(
                event_type="medication_stopped",
                when=record.end_date,
                fallback=record.created_at,
                title=f"پایان دارو: {name}",
                description=None,
                source_type="patient_medication",
                source_id=record.id,
            )

    for document in db.scalars(
        select(Document).where(Document.patient_id == patient.id)
    ):
        add(
            event_type="document_uploaded",
            when=document.created_at,
            fallback=document.created_at,
            title=f"سند: {document.title}",
            description=document.file_name,
            source_type="document",
            source_id=document.id,
        )

    for voice_note in db.scalars(
        select(VoiceNote).where(VoiceNote.patient_id == patient.id)
    ):
        add(
            event_type="voice_note_recorded",
            when=voice_note.created_at,
            fallback=voice_note.created_at,
            title=f"یادداشت صوتی: {voice_note.title or 'بدون عنوان'}",
            description=None,
            source_type="voice_note",
            source_id=voice_note.id,
        )

    for note in db.scalars(
        select(ClinicalNote).where(ClinicalNote.patient_id == patient.id)
    ):
        add(
            event_type="note_created",
            when=note.created_at,
            fallback=note.created_at,
            title=f"یادداشت بالینی: {note.title}",
            description=None,
            source_type="clinical_note",
            source_id=note.id,
        )

    for lab in db.scalars(
        select(LabResult).where(LabResult.patient_id == patient.id)
    ):
        value = lab.value + (f" {lab.unit}" if lab.unit else "")
        description = (
            f"محدودهٔ مرجع: {lab.reference_range}" if lab.reference_range else None
        )
        add(
            event_type="lab_result",
            when=lab.result_date,
            fallback=lab.created_at,
            title=f"{lab.test_name}: {value}",
            description=description,
            source_type="lab_result",
            source_id=lab.id,
        )

    items.sort(
        key=lambda item: (item.date, item.source_type, item.source_id),
        reverse=True,
    )
    return items
