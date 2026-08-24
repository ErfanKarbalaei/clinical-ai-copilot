"""Aggregated router for API v1.

Future feature routers (patients, documents, voice notes, ...) will be
registered here as they are implemented.
"""

from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
