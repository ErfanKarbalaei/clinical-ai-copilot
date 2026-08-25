"""Application configuration.

Settings are loaded from environment variables (12-factor style) with an
optional `.env` file. When running from the `backend/` directory the
repository-root `.env` (one level up) is used as a fallback, so a single
root `.env` can serve docker-compose, the backend, and the frontend.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, environment-based application settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Application ---
    PROJECT_NAME: str = "Clinical AI Copilot"
    PROJECT_DESCRIPTION: str = (
        "Clinical decision-support copilot for physicians (academic project). "
        "AI output is decision support only; the final decision always "
        "remains with the physician."
    )
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    BACKEND_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    # Comma-separated list of allowed browser origins (frontend dev server).
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- PostgreSQL ---
    POSTGRES_DB: str = "clinical_ai_copilot"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # --- MinIO / S3-compatible object storage ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "clinical-documents"
    MINIO_SECURE: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list of origins."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> str:
        """Synchronous SQLAlchemy connection URL."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (created once per process)."""
    return Settings()
