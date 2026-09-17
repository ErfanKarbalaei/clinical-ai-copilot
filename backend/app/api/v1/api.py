"""Aggregated router for API v1.

Future feature routers (documents, voice notes, ...) will be
registered here as they are implemented.
"""

from fastapi import APIRouter

from app.api.v1.routes.ai_medication_safety import router as ai_medication_safety_router
from app.api.v1.routes.agent import router as agent_router
from app.api.v1.routes.allergies import router as allergies_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.conditions import router as conditions_router
from app.api.v1.routes.conversations import router as conversations_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.medication_safety import router as medication_safety_router
from app.api.v1.routes.medications import router as medications_router
from app.api.v1.routes.patients import router as patients_router
from app.api.v1.routes.voice_notes import router as voice_notes_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(patients_router)
api_router.include_router(conditions_router)
api_router.include_router(allergies_router)
api_router.include_router(medications_router)
api_router.include_router(documents_router)
api_router.include_router(voice_notes_router)
api_router.include_router(chat_router)
api_router.include_router(medication_safety_router)
api_router.include_router(ai_medication_safety_router)
api_router.include_router(conversations_router)
api_router.include_router(agent_router)
