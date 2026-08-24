"""Pydantic schemas for the patient API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, PastDate

from app.models.enums import Gender
from app.schemas.allergy import AllergyResponse
from app.schemas.clinical_note import ClinicalNoteResponse
from app.schemas.condition import ConditionResponse
from app.schemas.lab_result import LabResultResponse
from app.schemas.medication import PatientMedicationResponse


class PatientBase(BaseModel):
    """Shared patient fields (used by create/response schemas)."""

    first_name: str = Field(min_length=1, max_length=100, description="نام")
    last_name: str = Field(min_length=1, max_length=100, description="نام خانوادگی")
    national_code: str | None = Field(
        default=None,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="کد ملی — دقیقاً ۱۰ رقم، یکتا",
    )
    date_of_birth: PastDate | None = Field(default=None, description="تاریخ تولد")
    gender: Gender = Field(default=Gender.unknown, description="جنسیت")
    phone: str | None = Field(default=None, max_length=20, description="شماره تماس")
    address: str | None = Field(default=None, description="نشانی")


class PatientCreate(PatientBase):
    """Payload for creating a patient."""


class PatientUpdate(BaseModel):
    """Payload for partially updating a patient (PATCH — all fields optional)."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    national_code: str | None = Field(
        default=None, min_length=10, max_length=10, pattern=r"^\d{10}$"
    )
    date_of_birth: PastDate | None = None
    gender: Gender | None = None
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = None


class PatientResponse(PatientBase):
    """Patient representation returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    """Paginated patient list."""

    items: list[PatientResponse]
    total: int


class PatientOverviewResponse(BaseModel):
    """Structured clinical overview of a patient (pure database data).

    No AI summary is generated here — every section is structured data
    read directly from the database.
    """

    patient: PatientResponse
    conditions: list[ConditionResponse] = Field(
        description="همهٔ مشکلات بالینی — فعال‌ها اول"
    )
    active_medications: list[PatientMedicationResponse] = Field(
        description="فقط داروهای فعال"
    )
    allergies: list[AllergyResponse] = Field(
        description="حساسیت‌ها — شدیدترها اول"
    )
    recent_lab_results: list[LabResultResponse] = Field(
        description="۵ نتیجهٔ آزمایش اخیر"
    )
    recent_clinical_notes: list[ClinicalNoteResponse] = Field(
        description="۵ یادداشت بالینی اخیر"
    )
