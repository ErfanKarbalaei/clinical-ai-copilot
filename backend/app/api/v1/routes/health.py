"""Health-check endpoint for API v1."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    """Report service liveness (monitoring / frontend readiness check)."""
    return HealthResponse(status="ok")
