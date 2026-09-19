"""Uniom messaging service — Soroush Plus text delivery for OTP (production).

Runtime path (NOT MCP): the backend calls the official Uniom REST API

    POST https://api.uniom.ir/bot<API_KEY>/sendMessage
    {"chat_id": "+989123456789", "text": "..."}

with an `uniom_...` API key (dashboard, scope ``bot:send``) bound to the
linked Soroush Plus credential. The MCP PAT is for Claude Code tooling only
and is never used here. Verified live via MCP (Task 21 feasibility):
personal Soroush Plus account, is_bot=false, phone-format chat_id works.
"""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# httpx logs request lines (full URL incl. the key) at INFO — silence it.
logging.getLogger("httpx").setLevel(logging.WARNING)


class UniomError(Exception):
    """Uniom returned an error or the request failed upstream."""


class UniomNotConfiguredError(Exception):
    """No UNIOM_API_KEY configured — messaging unavailable."""


class UniomMessagingService:
    """Send text messages through the linked Soroush Plus account.

    OTP logic stays fully decoupled: it only sees ``send_message`` and the
    two exceptions above. Secrets never appear in logs or responses.
    """

    def __init__(self, *, api_key: str | None = None):
        self._api_key = api_key  # None → read from settings per call (tests)

    def send_message(self, recipient: str, message: str) -> dict[str, Any]:
        """Send one text; returns the documented ``result`` object.

        Raises UniomNotConfiguredError / UniomError — never fakes success.
        """
        settings = get_settings()
        api_key = self._api_key or settings.UNIOM_API_KEY
        if not api_key:
            raise UniomNotConfiguredError("UNIOM_API_KEY is not configured")

        url = f"{settings.UNIOM_API_BASE_URL}/bot{api_key}/sendMessage"
        logger.info(
            "[uniom] send -> %s (recipient=%r, %d chars)",
            settings.UNIOM_API_BASE_URL, recipient, len(message),
        )
        try:
            with httpx.Client(
                timeout=httpx.Timeout(settings.UNIOM_TIMEOUT_SECONDS)
            ) as client:
                response = client.post(
                    url, json={"chat_id": recipient, "text": message}
                )
        except httpx.TimeoutException as error:
            raise UniomError(
                f"uniom timeout after {settings.UNIOM_TIMEOUT_SECONDS}s"
            ) from None
        except httpx.HTTPError as error:
            raise UniomError(f"uniom request failed: {type(error).__name__}") from None

        try:
            body = response.json()
        except ValueError:
            raise UniomError(
                f"uniom non-JSON response (HTTP {response.status_code})"
            ) from None

        if response.status_code == 200 and body.get("ok") is True:
            result = body.get("result") or {}
            logger.info(
                "[uniom] delivered (message_id=%s, recipient=%r)",
                result.get("message_id"), recipient,
            )
            return result

        error_code = body.get("error_code", response.status_code)
        description = str(body.get("description", "no description"))[:300]
        raise UniomError(f"uniom error {error_code}: {description}")


# Module-level singleton (tests monkeypatch `get_service`).
_service: UniomMessagingService | None = None


def get_service() -> UniomMessagingService:
    global _service
    if _service is None:
        _service = UniomMessagingService()
    return _service
