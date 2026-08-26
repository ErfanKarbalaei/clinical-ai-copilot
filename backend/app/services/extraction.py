"""Deterministic document text extraction — NO AI/LLM, fixed tools only.

Strategies by mime type:

- ``text/plain``        → decode as UTF-8
- ``application/pdf``   → embedded text layer via pypdf; when a page has
                          (almost) no text layer (a scan), fall back to OCR
                          over the page's embedded images
- images (png/jpeg/webp)→ OCR via Tesseract

OCR is OPTIONAL: when the Tesseract binary is not installed, text-based
PDFs still extract, and scanned/image documents fail with a clear reason
(``ExtractionUnavailable``) instead of crashing.
"""

import io
import logging
from dataclasses import dataclass

from pypdf import PdfReader

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# A PDF whose text layer is shorter than this is treated as a scan.
MIN_PDF_TEXT_CHARS = 50
MAX_PDF_PAGES = 50  # defensive cap for pathological documents


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: str  # plain_text | pdf_text | pdf_ocr | image_ocr


class ExtractionError(Exception):
    """Extraction could not be performed (OCR missing or unsupported type)."""


class ExtractionUnsupported(ExtractionError):
    """The mime type has no extraction strategy."""


class ExtractionUnavailable(ExtractionError):
    """OCR is required but the Tesseract binary is not available."""


_tesseract_ready: bool | None = None
_tesseract_languages: set[str] = set()


def _init_tesseract() -> bool:
    """Try to locate Tesseract once; remember the result and its languages."""
    global _tesseract_ready, _tesseract_languages
    if _tesseract_ready is not None:
        return _tesseract_ready
    _tesseract_ready = False
    _tesseract_languages = set()
    try:
        import pytesseract

        cmd = get_settings().TESSERACT_CMD
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        pytesseract.get_tesseract_version()  # raises when binary is missing
        _tesseract_languages = set(pytesseract.get_languages(config=""))
        _tesseract_ready = True
        logger.info(
            "Tesseract OCR available (languages: %s)", sorted(_tesseract_languages)
        )
    except Exception as error:  # noqa: BLE001 — any failure means "no OCR"
        logger.warning("Tesseract OCR unavailable: %s", error)
    return _tesseract_ready


def _ocr_language() -> str:
    """Prefer fas+eng (Persian + Latin), degrade to whatever is installed."""
    if {"fas", "eng"} <= _tesseract_languages:
        return "fas+eng"
    for language in ("fas", "eng"):
        if language in _tesseract_languages:
            return language
    return "eng"


def _ocr_image_bytes(data: bytes) -> str:
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    return pytesseract.image_to_string(image, lang=_ocr_language())


def _extract_pdf(data: bytes) -> ExtractionResult:
    reader = PdfReader(io.BytesIO(data))
    pages = reader.pages[:MAX_PDF_PAGES]

    text_parts = [(page.extract_text() or "").strip() for page in pages]
    layered_text = "\n".join(part for part in text_parts if part)

    if len(layered_text) >= MIN_PDF_TEXT_CHARS:
        return ExtractionResult(text=layered_text, method="pdf_text")

    # Little or no text layer → treat as a scan: OCR the embedded images.
    if not _init_tesseract():
        raise ExtractionUnavailable(
            "PDF has no text layer and Tesseract OCR is not installed"
        )
    ocr_parts: list[str] = []
    for page in pages:
        for image in page.images:
            try:
                ocr_parts.append(_ocr_image_bytes(image.data))
            except Exception as error:  # noqa: BLE001 — skip unreadable images
                logger.warning("PDF image OCR failed: %s", error)
    ocr_text = "\n".join(part.strip() for part in ocr_parts if part.strip())
    if ocr_text:
        return ExtractionResult(text=ocr_text, method="pdf_ocr")
    # No embedded images either — return whatever text layer existed.
    return ExtractionResult(text=layered_text, method="pdf_text")


def extract_text(*, mime_type: str, data: bytes) -> ExtractionResult:
    """Extract text from a stored document (pure, no database access)."""
    if mime_type == "text/plain":
        return ExtractionResult(
            text=data.decode("utf-8", errors="replace"), method="plain_text"
        )
    if mime_type == "application/pdf":
        return _extract_pdf(data)
    if mime_type in {"image/png", "image/jpeg", "image/webp"}:
        if not _init_tesseract():
            raise ExtractionUnavailable(
                f"OCR required for {mime_type} but Tesseract is not installed"
            )
        return ExtractionResult(text=_ocr_image_bytes(data), method="image_ocr")
    raise ExtractionUnsupported(f"no extraction strategy for {mime_type}")
