"""Model and relationship tests (require a running PostgreSQL)."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Allergy,
    ClinicalEvent,
    ClinicalNote,
    Condition,
    Document,
    LabResult,
    Medication,
    Patient,
    PatientMedication,
    VoiceNote,
)
from app.models.enums import (
    AllergySeverity,
    ConversationType,
    DocumentType,
    ExtractionStatus,
    Gender,
    MedicationStatus,
    NoteSource,
    ResultFlag,
    TranscriptionStatus,
)


def _sample_patient(**overrides) -> Patient:
    defaults = {"first_name": "علی", "last_name": "رضایی", "national_code": "1234567890"}
    defaults.update(overrides)
    return Patient(**defaults)


def test_create_patient_with_defaults(db_session):
    patient = _sample_patient()
    db_session.add(patient)
    db_session.flush()

    assert patient.id is not None
    assert patient.gender is Gender.unknown
    assert patient.created_at is not None


def test_national_code_must_be_unique(db_session):
    db_session.add(_sample_patient())
    db_session.flush()

    db_session.add(_sample_patient(first_name="مریم", last_name="احمدی"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_document_and_voice_note_defaults(db_session):
    patient = _sample_patient(national_code=None)
    document = Document(
        patient=patient,
        title="آزمایش خون",
        storage_key="patients/1/documents/lab.pdf",
        file_name="lab.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
    )
    voice_note = VoiceNote(patient=patient, audio_storage_key="patients/1/voice/note.m4a")
    db_session.add_all([document, voice_note])
    db_session.flush()

    assert document.doc_type is DocumentType.other
    assert document.extraction_status is ExtractionStatus.pending
    assert document.extracted_text is None
    assert voice_note.conversation_type is ConversationType.physician_note
    assert voice_note.transcription_status is TranscriptionStatus.pending
    assert voice_note.language == "fa"


def test_patient_medication_links_patient_to_catalog(db_session):
    patient = _sample_patient(national_code=None)
    metformin = Medication(name="Metformin 500", generic_name="Metformin")
    record = PatientMedication(
        patient=patient,
        medication=metformin,
        dosage="500 mg",
        frequency="دو بار در روز",
        start_date=date(2026, 1, 5),
    )
    db_session.add(record)
    db_session.flush()

    assert record.medication_id == metformin.id
    assert patient.patient_medications == [record]
    assert record.status is MedicationStatus.active


def test_clinical_note_derived_from_voice_note(db_session):
    patient = _sample_patient(national_code=None)
    voice_note = VoiceNote(
        patient=patient,
        audio_storage_key="patients/1/voice/v.m4a",
        transcript="متن خام گفتار",
    )
    note = ClinicalNote(
        patient=patient,
        title="یادداشت ویزیت",
        content="خلاصه بازبینی‌شده",
        source=NoteSource.voice,
        voice_note=voice_note,
    )
    db_session.add(note)
    db_session.flush()
    assert note.voice_note_id == voice_note.id

    # Deleting the original recording keeps the note (FK is set to NULL).
    db_session.delete(voice_note)
    db_session.flush()

    stored = db_session.execute(
        select(ClinicalNote.voice_note_id).where(ClinicalNote.id == note.id)
    ).scalar_one()
    assert stored is None


def test_lab_result_links_to_source_document(db_session):
    patient = _sample_patient(national_code=None)
    document = Document(
        patient=patient,
        title="گزارش آزمایش",
        storage_key="patients/1/documents/l.pdf",
        file_name="l.pdf",
        mime_type="application/pdf",
        file_size_bytes=1,
    )
    lab_result = LabResult(
        patient=patient,
        document=document,
        test_name="HbA1c",
        value="8.2",
        unit="%",
        reference_range="4.0-6.0",
        flag=ResultFlag.abnormal,
        result_date=date(2026, 7, 15),
    )
    db_session.add(lab_result)
    db_session.flush()
    assert lab_result.document_id == document.id

    # Deleting the source document keeps the structured value.
    db_session.delete(document)
    db_session.flush()
    db_session.refresh(lab_result)
    assert lab_result.document_id is None


def test_deleting_patient_cascades_to_all_clinical_data(db_session):
    patient = _sample_patient(national_code=None)
    medication = Medication(name="Test Drug")
    patient.conditions.append(Condition(name="دیابت نوع ۲"))
    patient.allergies.append(Allergy(allergen="پنی‌سیلین", severity=AllergySeverity.severe))
    patient.patient_medications.append(PatientMedication(medication=medication, dosage="10 mg"))
    patient.documents.append(
        Document(
            title="آزمایش",
            storage_key="k-doc",
            file_name="a.pdf",
            mime_type="application/pdf",
            file_size_bytes=1,
        )
    )
    patient.voice_notes.append(VoiceNote(audio_storage_key="k-audio"))
    patient.clinical_notes.append(ClinicalNote(title="یادداشت", content="متن"))
    patient.lab_results.append(LabResult(test_name="FBS", value="110"))
    patient.clinical_events.append(
        ClinicalEvent(
            event_type="visit",
            event_date=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
            title="ویزیت",
        )
    )
    db_session.add(patient)
    db_session.flush()
    patient_id = patient.id

    db_session.delete(patient)
    db_session.flush()

    children = (
        Condition,
        Allergy,
        PatientMedication,
        Document,
        VoiceNote,
        ClinicalNote,
        LabResult,
        ClinicalEvent,
    )
    for entity in children:
        assert db_session.query(entity).filter_by(patient_id=patient_id).count() == 0
    # The catalog medication survives — only the patient link is removed.
    assert db_session.query(Medication).count() == 1
