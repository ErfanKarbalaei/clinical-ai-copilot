"""Pydantic schemas for the patient medication API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MedicationStatus


class MedicationBrief(BaseModel):
    """Catalog information about a medication."""

    id: int
    name: str
    generic_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientMedicationCreate(BaseModel):
    """Payload for adding a medication to a patient.

    Reference the catalog either by ``medication_id`` or by
    ``medication_name`` (an existing catalog entry is reused, otherwise a
    new one is created) — exactly one of the two must be provided.
    """

    medication_id: int | None = Field(default=None, description="شناسهٔ دارو در کاتالوگ")
    medication_name: str | None = Field(
        default=None, min_length=1, max_length=200, description="نام دارو (ایجاد/استفادهٔ خودکار)"
    )
    generic_name: str | None = Field(
        default=None, max_length=200, description="نام ژنریک (فقط هنگام ایجاد داروی جدید)"
    )
    dosage: str | None = Field(default=None, max_length=100, description="دوز")
    frequency: str | None = Field(default=None, max_length=100, description="تناوب مصرف")
    status: MedicationStatus = Field(
        default=MedicationStatus.active,
        description="وضعیت (active/stopped/completed)",
    )
    start_date: date | None = Field(default=None, description="تاریخ شروع")
    end_date: date | None = Field(default=None, description="تاریخ پایان")
    notes: str | None = Field(default=None, description="توضیحات/دستور مصرف")

    @model_validator(mode="after")
    def exactly_one_medication_reference(self) -> "PatientMedicationCreate":
        has_id = self.medication_id is not None
        has_name = self.medication_name is not None
        if has_id and has_name:
            raise ValueError(
                "نمی‌توان هم medication_id و هم medication_name را ارسال کرد."
            )
        if not has_id and not has_name:
            raise ValueError("medication_id یا medication_name باید ارسال شود.")
        return self

    @property
    def record_fields(self) -> dict:
        """Fields that map directly onto the PatientMedication model."""
        return self.model_dump(
            exclude={"medication_id", "medication_name", "generic_name"}
        )


class PatientMedicationUpdate(BaseModel):
    """Payload for partially updating a patient medication."""

    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    status: MedicationStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class PatientMedicationResponse(BaseModel):
    """Patient medication representation (includes catalog info)."""

    id: int
    patient_id: int
    medication: MedicationBrief
    dosage: str | None = None
    frequency: str | None = None
    status: MedicationStatus
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
