"""Seed the development database with sample clinical data.

DEVELOPMENT ONLY — this inserts clearly fictional sample data so the
schema can be explored and queried during development. It is never used
in (or suitable for) production.

Notes:
- ``storage_key`` / ``audio_storage_key`` values reference MinIO object
  keys, but this script does NOT upload any files — it stores metadata
  rows only.
- The script refuses to run when patients already exist, unless
  ``--reset`` is passed (which wipes all clinical tables first).
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
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
    NoteSource,
    ResultFlag,
    TranscriptionStatus,
)


def _dt(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _event(
    patient: Patient,
    event_type: str,
    when: datetime,
    title: str,
    description: Optional[str] = None,
    source: Optional[object] = None,
) -> ClinicalEvent:
    """Build a timeline event, deriving source_type/source_id from a model row."""
    return ClinicalEvent(
        patient=patient,
        event_type=event_type,
        event_date=when,
        title=title,
        description=description,
        source_type=source.__tablename__ if source is not None else None,
        source_id=source.id if source is not None else None,
    )


def _medications() -> list[Medication]:
    return [
        Medication(name="Metformin 500", generic_name="Metformin"),
        Medication(name="Losartan 50", generic_name="Losartan"),
        Medication(name="Levothyroxine 100", generic_name="Levothyroxine"),
        Medication(name="Albuterol Inhaler", generic_name="Salbutamol"),
    ]


def _patient_ali(session: Session, medications: dict[str, Medication]) -> Patient:
    patient = Patient(
        first_name="علی",
        last_name="رضایی",
        national_code="0012345678",
        date_of_birth=date(1968, 5, 14),
        gender="male",
        phone="09121234567",
    )
    diabetes = Condition(
        name="دیابت نوع ۲ (Type 2 Diabetes)",
        onset_date=date(2019, 3, 10),
        notes="کنترل نامطلوب در ویزیت اخیر",
    )
    hypertension = Condition(
        name="پرفشاری خون (Hypertension)",
        onset_date=date(2016, 9, 1),
    )
    patient.conditions = [diabetes, hypertension]
    patient.allergies = [
        Allergy(
            allergen="پنی‌سیلین (Penicillin)",
            reaction="کهیر و تنگی نفس",
            severity=AllergySeverity.severe,
        )
    ]
    metformin = PatientMedication(
        medication=medications["Metformin 500"],
        dosage="500 mg",
        frequency="دو بار در روز",
        start_date=date(2019, 3, 10),
    )
    losartan = PatientMedication(
        medication=medications["Losartan 50"],
        dosage="50 mg",
        frequency="هر شب",
        start_date=date(2016, 9, 1),
    )
    patient.patient_medications = [metformin, losartan]

    session.add(patient)
    session.flush()  # patient.id is needed for storage keys

    lab_document = Document(
        patient=patient,
        title="آزمایش خون — ژوئیه ۲۰۲۶",
        doc_type=DocumentType.lab_report,
        storage_key=f"patients/{patient.id}/documents/2026-07-lab-report.pdf",
        file_name="lab-report-2026-07.pdf",
        mime_type="application/pdf",
        file_size_bytes=204_800,
        extraction_status=ExtractionStatus.completed,
        extracted_text="HbA1c: 8.2 %\nFBS: 168 mg/dL\nLDL: 140 mg/dL",
    )
    pending_voice_note = VoiceNote(
        patient=patient,
        title="یادداشت صوتی کوتاه",
        conversation_type=ConversationType.physician_note,
        audio_storage_key=f"patients/{patient.id}/voice/2026-08-20-note.m4a",
        duration_seconds=62,
        transcription_status=TranscriptionStatus.pending,
    )
    visit_note = ClinicalNote(
        patient=patient,
        title="خلاصه ویزیت — کنترل دیابت",
        content=(
            "قند ناشتای بیمار بالا است؛ دوز متفورمین افزایش داده شد و "
            "رژیم غذایی بازنگری گردید. کنترل مجدد در سه ماه آینده."
        ),
        source=NoteSource.manual,
    )
    hba1c = LabResult(
        patient=patient,
        document=lab_document,
        test_name="HbA1c",
        value="8.2",
        unit="%",
        reference_range="4.0-6.0",
        flag=ResultFlag.abnormal,
        result_date=date(2026, 7, 15),
    )
    fbs = LabResult(
        patient=patient,
        document=lab_document,
        test_name="FBS",
        value="168",
        unit="mg/dL",
        reference_range="70-110",
        flag=ResultFlag.abnormal,
        result_date=date(2026, 7, 15),
    )
    ldl = LabResult(
        patient=patient,
        document=lab_document,
        test_name="LDL",
        value="140",
        unit="mg/dL",
        reference_range="<100",
        flag=ResultFlag.abnormal,
        result_date=date(2026, 7, 15),
    )
    session.add_all(
        [lab_document, pending_voice_note, visit_note, hba1c, fbs, ldl]
    )
    session.flush()

    session.add_all(
        [
            _event(patient, "condition_onset", _dt(2016, 9, 1), "تشخیص پرفشاری خون", source=hypertension),
            _event(patient, "medication_started", _dt(2016, 9, 1), "شروع Losartan", source=losartan),
            _event(patient, "condition_onset", _dt(2019, 3, 10), "تشخیص دیابت نوع ۲", source=diabetes),
            _event(patient, "medication_started", _dt(2019, 3, 10), "شروع Metformin", source=metformin),
            _event(
                patient, "document_uploaded", _dt(2026, 7, 15),
                "بارگذاری آزمایش خون", description="گزارش آزمایشگاه (PDF)", source=lab_document,
            ),
            _event(
                patient, "lab_result", _dt(2026, 7, 15),
                "HbA1c: 8.2٪ — خارج از محدوده طبیعی", source=hba1c,
            ),
            _event(patient, "note_created", _dt(2026, 8, 1), "ثبت خلاصه ویزیت", source=visit_note),
            _event(
                patient, "voice_note_recorded", _dt(2026, 8, 20),
                "یادداشت صوتی جدید (در انتظار تبدیل به متن)", source=pending_voice_note,
            ),
        ]
    )
    return patient


def _patient_maryam(session: Session, medications: dict[str, Medication]) -> Patient:
    patient = Patient(
        first_name="مریم",
        last_name="احمدی",
        national_code="0023456789",
        date_of_birth=date(1985, 11, 2),
        gender="female",
    )
    hypothyroidism = Condition(
        name="کم‌کاری تیروئید (Hypothyroidism)",
        onset_date=date(2020, 6, 1),
    )
    patient.conditions = [hypothyroidism]
    levothyroxine = PatientMedication(
        medication=medications["Levothyroxine 100"],
        dosage="100 mcg",
        frequency="روزانه، ناشتا",
        start_date=date(2020, 6, 1),
    )
    patient.patient_medications = [levothyroxine]

    session.add(patient)
    session.flush()

    thyroid_document = Document(
        patient=patient,
        title="آزمایش تیروئید — اوت ۲۰۲۶",
        doc_type=DocumentType.lab_report,
        storage_key=f"patients/{patient.id}/documents/2026-08-thyroid.pdf",
        file_name="thyroid-2026-08.pdf",
        mime_type="application/pdf",
        file_size_bytes=153_600,
        extraction_status=ExtractionStatus.completed,
        extracted_text="TSH: 2.4 mIU/L",
    )
    voice_note = VoiceNote(
        patient=patient,
        title="یادداشت صوتی ویزیت",
        conversation_type=ConversationType.physician_note,
        audio_storage_key=f"patients/{patient.id}/voice/2026-08-10-note.m4a",
        duration_seconds=95,
        transcription_status=TranscriptionStatus.completed,
        transcript=(
            "بیمار چهل‌ساله با سابقه کم‌کاری تیروئید تحت درمان با لووتیروکسین. "
            "عارضه جانبی گزارش نشده. TSH در محدوده طبیعی؛ ادامه درمان با دوز فعلی."
        ),
    )
    note = ClinicalNote(
        patient=patient,
        voice_note=voice_note,
        title="خلاصه ویزیت تیروئید",
        content=(
            "پیگیری کم‌کاری تیروئید؛ TSH در محدوده طبیعی است و لووتیروکسین "
            "با دوز فعلی ادامه می‌یابد. ویزیت بعدی شش ماه دیگر."
        ),
        source=NoteSource.voice,
    )
    tsh = LabResult(
        patient=patient,
        document=thyroid_document,
        test_name="TSH",
        value="2.4",
        unit="mIU/L",
        reference_range="0.4-4.0",
        flag=ResultFlag.normal,
        result_date=date(2026, 8, 10),
    )
    session.add_all([thyroid_document, voice_note, note, tsh])
    session.flush()

    session.add_all(
        [
            _event(patient, "condition_onset", _dt(2020, 6, 1), "تشخیص کم‌کاری تیروئید", source=hypothyroidism),
            _event(patient, "medication_started", _dt(2020, 6, 1), "شروع Levothyroxine", source=levothyroxine),
            _event(
                patient, "lab_result", _dt(2026, 8, 10),
                "TSH: 2.4 — در محدوده طبیعی", source=tsh,
            ),
            _event(patient, "voice_note_recorded", _dt(2026, 8, 10), "ثبت یادداشت صوتی ویزیت", source=voice_note),
            _event(
                patient, "note_created", _dt(2026, 8, 10),
                "ثبت یادداشت بالینی از روی یادداشت صوتی", source=note,
            ),
        ]
    )
    return patient


def _patient_hossein(session: Session, medications: dict[str, Medication]) -> Patient:
    patient = Patient(
        first_name="حسین",
        last_name="کریمی",
        national_code="0034567890",
        date_of_birth=date(1957, 3, 20),
        gender="male",
    )
    asthma = Condition(name="آسم (Asthma)", onset_date=date(2005, 4, 1))
    bronchitis = Condition(
        name="برونشیت حاد (Acute Bronchitis)",
        onset_date=date(2022, 1, 15),
        resolved_date=date(2022, 2, 20),
        status="resolved",
    )
    patient.conditions = [asthma, bronchitis]
    patient.allergies = [
        Allergy(allergen="آسپرین (Aspirin)", reaction="کهیر", severity=AllergySeverity.moderate)
    ]
    inhaler = PatientMedication(
        medication=medications["Albuterol Inhaler"],
        dosage="100 mcg/puff",
        frequency="در صورت نیاز (PRN)",
        start_date=date(2005, 4, 1),
    )
    patient.patient_medications = [inhaler]

    session.add(patient)
    session.flush()

    imaging_document = Document(
        patient=patient,
        title="گزارش رادیوگرافی قفسه سینه",
        doc_type=DocumentType.imaging_report,
        storage_key=f"patients/{patient.id}/documents/2026-06-20-cxr.pdf",
        file_name="cxr-report.pdf",
        mime_type="application/pdf",
        file_size_bytes=348_160,
        extraction_status=ExtractionStatus.pending,
    )
    conversation = VoiceNote(
        patient=patient,
        title="گفتگوی پزشک و بیمار",
        conversation_type=ConversationType.doctor_patient,
        audio_storage_key=f"patients/{patient.id}/voice/2026-08-18-conversation.m4a",
        duration_seconds=412,
        transcription_status=TranscriptionStatus.completed,
        transcript=(
            "پزشک: امروز سرفه چطوره؟\n"
            "بیمار: شب‌ها بیشتر می‌شه و صدای خس‌خس هم دارم.\n"
            "پزشک: اسپری را طبق دستور استفاده می‌کنید؟\n"
            "بیمار: بله، ولی گاهی فراموش می‌کنم."
        ),
    )
    note = ClinicalNote(
        patient=patient,
        title="خلاصه ویزیت تنفسی",
        content=(
            "شکایت اصلی سرفه شبانه و خس‌خس سینه؛ ادامه اسپری آلبوترول و "
            "آموزش مصرف منظم. در صورت تشدید علائم، مراجعه فوری."
        ),
        source=NoteSource.manual,
    )
    fev1 = LabResult(
        patient=patient,
        test_name="FEV1",
        value="68",
        unit="%",
        reference_range=">=80",
        flag=ResultFlag.abnormal,
        result_date=date(2026, 6, 18),
    )
    session.add_all([imaging_document, conversation, note, fev1])
    session.flush()

    session.add_all(
        [
            _event(patient, "condition_onset", _dt(2005, 4, 1), "تشخیص آسم", source=asthma),
            _event(patient, "medication_started", _dt(2005, 4, 1), "شروع اسپری آلبوترول", source=inhaler),
            _event(patient, "condition_onset", _dt(2022, 1, 15), "تشخیص برونشیت حاد", source=bronchitis),
            _event(
                patient, "document_uploaded", _dt(2026, 6, 20),
                "بارگذاری گزارش رادیوگرافی", description="در انتظار استخراج متن", source=imaging_document,
            ),
            _event(
                patient, "voice_note_recorded", _dt(2026, 8, 18),
                "ضبط گفتگوی پزشک و بیمار", source=conversation,
            ),
            _event(patient, "note_created", _dt(2026, 8, 18), "ثبت خلاصه ویزیت تنفسی", source=note),
        ]
    )
    return patient


def run(session: Session | None = None, reset: bool = False) -> dict[str, int]:
    """Insert the sample data and return row counts per table.

    Accepts an external session (used by tests); otherwise a new session
    from the application session factory is used.
    """
    owns_session = session is None
    if session is None:
        session = SessionLocal()
    try:
        if reset:
            session.execute(
                delete(Patient).execution_options(synchronize_session=False)
            )
            session.execute(
                delete(Medication).execution_options(synchronize_session=False)
            )
            session.commit()
        elif session.query(Patient.id).limit(1).count():
            raise RuntimeError(
                "database already contains patients; re-run with --reset "
                "(or reset=True) to wipe and reseed"
            )

        medications = {med.name: med for med in _medications()}
        session.add_all(medications.values())

        for builder in (_patient_ali, _patient_maryam, _patient_hossein):
            builder(session, medications)

        session.commit()

        return {
            "patients": session.query(Patient).count(),
            "conditions": session.query(Condition).count(),
            "medications": session.query(Medication).count(),
            "patient_medications": session.query(PatientMedication).count(),
            "allergies": session.query(Allergy).count(),
            "documents": session.query(Document).count(),
            "voice_notes": session.query(VoiceNote).count(),
            "clinical_notes": session.query(ClinicalNote).count(),
            "lab_results": session.query(LabResult).count(),
            "clinical_events": session.query(ClinicalEvent).count(),
        }
    finally:
        if owns_session:
            session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the development database with sample clinical data."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="wipe all clinical tables before seeding",
    )
    args = parser.parse_args()

    try:
        counts = run(reset=args.reset)
    except RuntimeError as error:
        print(f"ERROR: {error}")
        raise SystemExit(1) from None

    print("Seed completed. Row counts:")
    for table, count in counts.items():
        print(f"  {table:<20} {count}")


if __name__ == "__main__":
    main()
