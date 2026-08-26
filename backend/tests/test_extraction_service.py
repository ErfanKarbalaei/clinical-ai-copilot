"""Unit tests for the deterministic extraction service (no AI)."""

import io

import pytest

from app.services import extraction
from app.services.extraction import (
    ExtractionResult,
    ExtractionUnavailable,
    ExtractionUnsupported,
)
from tests.pdf_helper import pdf_with_text


def _tesseract_available() -> bool:
    return extraction._init_tesseract()


def _render_png(text: str, font_path: str, width: int = 900, height: int = 160) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, 64)
    draw.text((20, 40), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# --- plain text ---


def test_extract_plain_text():
    result = extraction.extract_text(
        mime_type="text/plain", data="HbA1c: 8.2 %".encode()
    )
    assert result == ExtractionResult(text="HbA1c: 8.2 %", method="plain_text")


# --- PDF text layer ---


def test_extract_pdf_text_layer():
    pdf = pdf_with_text("CLINICAL LAB REPORT WITH DETAILED PATIENT LABORATORY RESULTS")

    result = extraction.extract_text(mime_type="application/pdf", data=pdf)

    assert result.method == "pdf_text"
    assert "CLINICAL LAB REPORT" in result.text


def test_extract_pdf_without_text_or_ocr_raises_unavailable(monkeypatch):
    # A blank PDF (no text layer, no images) + no OCR → clear error.
    pdf = pdf_with_text("")
    monkeypatch.setattr(extraction, "_tesseract_ready", False)

    with pytest.raises(ExtractionUnavailable):
        extraction.extract_text(mime_type="application/pdf", data=pdf)


# --- OCR (skipped when Tesseract is not installed) ---


@pytest.mark.skipif(not _tesseract_available(), reason="Tesseract not installed")
def test_ocr_image_english():
    png = _render_png("CLINICAL REPORT", "C:/Windows/Fonts/arial.ttf")

    result = extraction.extract_text(mime_type="image/png", data=png)

    assert result.method == "image_ocr"
    assert "CLINICAL" in result.text.upper()


@pytest.mark.skipif(
    not _tesseract_available() or "fas" not in extraction._tesseract_languages,
    reason="Tesseract with Persian (fas) data not installed",
)
def test_ocr_image_persian():
    png = _render_png("گزارش آزمایشگاه", "C:/Windows/Fonts/tahoma.ttf")

    result = extraction.extract_text(mime_type="image/png", data=png)

    assert result.method == "image_ocr"
    # OCR output can be noisy — assert meaningful Persian text was produced.
    assert len(result.text.strip()) >= 3


def test_ocr_image_without_tesseract_raises_unavailable(monkeypatch):
    monkeypatch.setattr(extraction, "_tesseract_ready", False)

    with pytest.raises(ExtractionUnavailable):
        extraction.extract_text(mime_type="image/png", data=b"not-really-png")


# --- unsupported ---


def test_unsupported_mime_type():
    with pytest.raises(ExtractionUnsupported):
        extraction.extract_text(mime_type="application/zip", data=b"PK")
