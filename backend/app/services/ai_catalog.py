"""Provider/model catalog for runtime AI selection (frontend discovery).

The frontend gets ONLY provider/model ids from here — never keys, never
URLs. Sources of truth:

- gemini: curated static list (Google AI Studio models used by this project)
- openrouter: public ``GET /v1/models`` (no key required)

Failures never fabricate models: a provider whose discovery fails is simply
omitted (and logged); the rest of the catalog stays usable. Results are
cached briefly so the chat UI does not hammer the gateways.
"""

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.ai import PROVIDER_IDS, _key_for

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, list[dict]]] = {}

# Curated Gemini list (static — no discovery endpoint used for it).
_GEMINI_MODELS = [
    {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash"},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
]

_PROVIDER_NAMES = {
    "gemini": "Gemini",
    "openrouter": "OpenRouter",
    "openai_compatible": "OpenAI-compatible",
}


def _fetch_openai_style_models(
    base_url: str, api_key: str | None, user_agent: str | None = None
) -> list[dict]:
    """GET <base>/models in the OpenAI format → [{id, name?}] (no fabrication)."""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if user_agent:
        headers["User-Agent"] = user_agent
    with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
        response = client.get(f"{base_url.rstrip('/')}/models", headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"/models returned HTTP {response.status_code}")
    data = response.json().get("data") or []
    return [
        {"id": str(item["id"]), "name": str(item.get("name") or item["id"])}
        for item in data
        if item.get("id")
    ]


def _provider_models(provider_id: str) -> list[dict]:
    """Models for one provider (cached); [] when unconfigured/unavailable."""
    settings = get_settings()
    cached = _cache.get(provider_id)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        if provider_id == "gemini":
            models = _GEMINI_MODELS if _key_for("gemini", settings) else []
        elif provider_id == "openrouter":
            # public catalog — works even before a key is set
            from app.services.ai import OPENROUTER_BASE_URL
            models = _fetch_openai_style_models(OPENROUTER_BASE_URL, _key_for("openrouter", settings))
        else:
            models = []
    except Exception as error:  # noqa: BLE001 — discovery failure ≠ app failure
        logger.warning("model discovery failed for %s: %s", provider_id, error)
        return []  # never fabricated

    _cache[provider_id] = (time.monotonic(), models)
    return models


def list_providers() -> list[dict[str, Any]]:
    """Catalog of configured providers with their discovered models."""
    settings = get_settings()
    providers = []
    for provider_id in PROVIDER_IDS:
        if provider_id == "openai_compatible" and not settings.AI_BASE_URL:
            continue
        if provider_id == "openai_compatible" and settings.AI_PROVIDER != "openai_compatible":
            continue  # only surface the generic provider when it is the default
        models = _provider_models(provider_id)
        if not models and provider_id != "openai_compatible":
            continue  # unconfigured or discovery failed — omit, don't fabricate
        providers.append(
            {
                "id": provider_id,
                "name": _PROVIDER_NAMES.get(provider_id, provider_id),
                "models": models,
            }
        )
    return providers


def invalidate_cache() -> None:
    """Test helper."""
    _cache.clear()
