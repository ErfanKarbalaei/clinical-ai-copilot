"""Application logging configuration."""

import io
import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Keep every created wrapper referenced for the process lifetime: an
# unreferenced TextIOWrapper is garbage-collected, and closing it would
# close the underlying stdout buffer (breaking all later I/O).
_wrapper_keepalive: list[io.TextIOWrapper] = []


def setup_logging(debug: bool = False) -> None:
    """Configure root logging once (stdout, single-line format).

    The stream is forced to UTF-8 with ``errors="replace"``: Windows consoles
    default to legacy codepages (e.g. cp1256) that cannot encode Persian
    text — without this, log calls with Persian content crash silently and
    the message is lost.
    """
    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. by uvicorn)
        for handler in root.handlers:
            _make_handler_utf8_safe(handler)
        return

    root.addHandler(_utf8_stdout_handler())
    root.setLevel(logging.DEBUG if debug else logging.INFO)


def _utf8_stdout_handler() -> logging.StreamHandler:
    wrapper = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    wrapper._clinical_utf8_wrapped = True  # type: ignore[attr-defined]
    _wrapper_keepalive.append(wrapper)
    handler = logging.StreamHandler(wrapper)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def _make_handler_utf8_safe(handler: logging.Handler) -> None:
    """Re-wrap an existing stream handler's stream as UTF-8 (uvicorn's)."""
    stream = getattr(handler, "stream", None)
    if stream is None or getattr(stream, "_clinical_utf8_wrapped", False):
        return
    buffer = getattr(stream, "buffer", None)
    if buffer is None:  # already a wrapper without a buffer — leave it
        return
    wrapper = io.TextIOWrapper(
        buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    wrapper._clinical_utf8_wrapped = True  # type: ignore[attr-defined]
    _wrapper_keepalive.append(wrapper)
    handler.stream = wrapper
