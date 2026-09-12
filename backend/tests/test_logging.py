"""Logging regression tests — Persian text must never crash a log call."""

import logging

from app.core.logging import setup_logging


def test_setup_logging_creates_utf8_stream():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    try:
        root.handlers = []  # force fresh setup
        setup_logging()
        handler = root.handlers[0]
        assert getattr(handler.stream, "encoding", "") == "utf-8"
    finally:
        root.handlers = original_handlers


def test_logging_persian_does_not_raise():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    try:
        root.handlers = []
        setup_logging()
        # Under a legacy Windows console codepage (cp1256) this used to raise
        # UnicodeEncodeError and silently drop the whole log record.
        logging.getLogger("test.persian").error(
            "AI provider failure (patient=%s, question=%r): %s",
            8, "خلاصهٔ وضعیت بیمار چیست؟", "provider unreachable",
        )
    finally:
        root.handlers = original_handlers
