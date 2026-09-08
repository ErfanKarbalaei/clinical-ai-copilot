"""FastAPI application entry point for the Clinical AI Copilot backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.schemas.health import HealthResponse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        debug=settings.DEBUG,
    )

    # The Next.js frontend calls the API cross-origin during development
    # (localhost:3000 by default, localhost:3100 for an alternate instance),
    # so CORS is part of the foundation. Override via CORS_ORIGINS in .env.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Versioned API surface — future feature routers are registered in
    # app/api/v1/api.py and mounted here automatically.
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Stable, non-versioned health endpoint for infrastructure probes
    # (same handler as the versioned one).
    @app.get("/health", response_model=HealthResponse, tags=["health"], summary="Health check")
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
