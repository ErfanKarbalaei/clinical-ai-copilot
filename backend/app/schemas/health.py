"""Schemas for health-check endpoints."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Service liveness report."""

    status: str
