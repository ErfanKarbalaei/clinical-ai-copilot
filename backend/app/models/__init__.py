"""SQLAlchemy ORM models.

Importing this package registers every model on the shared ``Base``
metadata — which is what Alembic autogenerate and
``Base.metadata.create_all`` rely on.
"""

from app.models.allergy import Allergy
from app.models.clinical_event import ClinicalEvent
from app.models.clinical_note import ClinicalNote
from app.models.condition import Condition
from app.models.document import Document
from app.models.lab_result import LabResult
from app.models.medication import Medication, PatientMedication
from app.models.patient import Patient
from app.models.voice_note import VoiceNote

__all__ = [
    "Allergy",
    "ClinicalEvent",
    "ClinicalNote",
    "Condition",
    "Document",
    "LabResult",
    "Medication",
    "Patient",
    "PatientMedication",
    "VoiceNote",
]
