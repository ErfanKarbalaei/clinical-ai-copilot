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
    # Comma-separated list of allowed browser origins. Frontend dev server
    # defaults to localhost:3000; localhost:3100 is the alternate instance
    # port. Override via CORS_ORIGINS in .env.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3100"

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

    # --- OCR (optional) ---
    # Absolute path to the tesseract binary; leave empty to use PATH lookup.
    TESSERACT_CMD: str = ""

    # --- Speech-to-Text (Speechmatics batch API) ---
    SPEECHMATICS_API_KEY: str = ""  # empty → transcription marked failed with reason
    SPEECHMATICS_BASE_URL: str = "https://asr.api.speechmatics.com/v2"
    STT_POLL_INTERVAL_SECONDS: float = 3.0
    STT_TIMEOUT_SECONDS: int = 300

    # --- AI assistant (provider-agnostic) ---
    # AI_PROVIDER: "openai_compatible" (any OpenAI-style chat/completions API)
    #              or "gemini" (native Google Gemini generateContent API)
    AI_PROVIDER: str = "openai_compatible"
    AI_API_KEY: str = ""  # empty → chat returns 503 with a Persian message
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gemini-3.6-flash"  # empty → provider default (gpt-4o-mini / gemini-2.5-flash)
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_HISTORY_TURNS: int = 6
    # Optional HTTP(S) proxy for reaching the AI provider from restricted
    # networks, e.g. http://127.0.0.1:7890 — empty = direct connection.
    AI_PROXY: str = ""

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
