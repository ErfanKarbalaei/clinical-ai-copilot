"""Application logging configuration."""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(debug: bool = False) -> None:
    """Configure root logging (single handler, stdout, one-line format).

    Safe to call multiple times: if logging is already configured
    (e.g. by a test runner), it is left untouched.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
