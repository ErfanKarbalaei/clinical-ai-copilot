# ============================================================
# Clinical AI Copilot — backend image
#
# Python 3.12 slim + Tesseract OCR (with Persian language data)
# Runs uvicorn as a non-root user on 0.0.0.0:8000.
# All runtime configuration comes from environment variables
# (POSTGRES_*, MINIO_*, JWT_*, AI_*, STT_* …) — nothing is
# hard-coded and no .env file is baked into the image.
# ============================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- system dependencies -------------------------------------------------
# tesseract-ocr + tesseract-ocr-fas: Persian OCR for document extraction
# (pytesseract needs the binary; the fas pack adds Persian language data).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-fas \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- python dependencies (cached layer) -----------------------------------
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- application code ------------------------------------------------------
# app/            — FastAPI application
# alembic/ + ini  — DB migrations (run as a separate step: alembic upgrade head)
# scripts/        — seed / migration helpers for deployments
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# --- non-root user ----------------------------------------------------------
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Lightweight liveness probe without extra tools (python is already there).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
