"""Provider-agnostic LLM access for the clinical AI assistant.

Two boring implementations behind one tiny interface (``LLMProvider``):

- ``OpenAICompatibleProvider`` — any OpenAI-style ``chat/completions`` API
  (OpenAI, OpenRouter, Azure-style gateways, local Ollama/vLLM/LM Studio)
- ``GeminiProvider`` — Google's native ``generateContent`` API (v1beta)

Switching providers is pure configuration: ``AI_PROVIDER`` selects the
implementation, ``AI_MODEL`` is optional (empty = provider default), and
``AI_PROXY`` can route requests through a proxy on restricted networks.
No SDK dependency (plain httpx), no RAG, no vector search — just prompt +
patient context. The provider instance is created lazily and cached; tests
swap it by monkeypatching :func:`get_provider`.

Transient transport failures (connection resets, truncated bodies — common
on filtered networks) are retried a few times before surfacing. Error
messages always carry the real provider failure so the backend log shows
what actually happened.
"""

import json
import logging
import time
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Transient transport errors worth retrying (resets / truncated bodies).
_RETRYABLE_TRANSPORT_ERRORS = (httpx.TransportError, httpx.RemoteProtocolError)
_HTTP_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0


class AIError(Exception):
    """The AI provider failed or rejected the request."""


class AIUnavailableError(AIError):
    """No AI provider configured (empty AI_API_KEY)."""


class AIInvalidSelectionError(AIError):
    """Client-supplied provider/model selection is not valid."""


SYSTEM_PROMPT = """You are a clinical decision-support assistant used by a physician.
You receive one patient's structured record (JSON) and the physician's question.

Rules:
- Ground every statement in the provided patient data; never invent findings,
  medications, doses, lab values, or diagnoses that are not in the data.
- If the data does not contain the answer, say so clearly and suggest what
  information or examination would be needed.
- You support decisions; the final decision always rests with the physician.
- Be concise and clinical. Use short paragraphs or bullet points.
- Respond in Persian (Farsi). Keep drug names and lab test names in their
  standard Latin form where that is how they appear in the data.
"""

# Per-text-field cap when serializing the context into the prompt.
_MAX_TEXT_FIELD_CHARS = 2000


class LLMProvider(Protocol):
    """Minimal provider interface (swap providers by implementing this)."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
    ) -> str: ...


def _post_with_retries(
    client: httpx.Client, url: str, *, headers: dict, json_body: dict
) -> httpx.Response:
    """POST with a few retries on transient transport failures.

    Filtered networks frequently reset connections mid-response; retrying
    turns those into a short delay instead of a user-facing failure.
    """
    last_error: Exception | None = None
    for attempt in range(1, _HTTP_ATTEMPTS + 1):
        try:
            return client.post(url, headers=headers, json=json_body)
        except _RETRYABLE_TRANSPORT_ERRORS as error:
            last_error = error
            logger.warning(
                "AI provider transport failure (attempt %d/%d): %s: %s",
                attempt, _HTTP_ATTEMPTS, type(error).__name__, error,
            )
            if attempt < _HTTP_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
    raise AIError(f"provider unreachable after {_HTTP_ATTEMPTS} attempts: {last_error}")


def _log_request(provider: str, method: str, url: str, *, model: str, key_present: bool) -> None:
    """One-line pre-request debug log — NEVER logs the API key itself."""
    logger.info(
        "[ai-request] provider=%s model=%s key_present=%s -> %s %s",
        provider, model, key_present, method, url,
    )


def _log_response(provider: str, response: httpx.Response) -> None:
    """Post-response debug log — status, headers of interest, body (≤1000 chars)."""
    logger.info(
        "[ai-response] provider=%s status=%s content-type=%s body[:1000]=%s",
        provider,
        response.status_code,
        response.headers.get("content-type", ""),
        response.text[:1000],
    )


def _http_client(timeout: float, proxy: str | None) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout),
        proxy=proxy or None,
    )


def _snippet(text: str, limit: int = 200) -> str:
    return " ".join(text.split())[:limit]


def _looks_like_json(response: httpx.Response, body_text: str) -> bool:
    content_type = response.headers.get("content-type", "")
    return content_type.startswith("application/json") or body_text.lstrip().startswith("{")


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions client (httpx, no SDK)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        proxy: str | None = None,
        extra_headers: dict[str, str] | None = None,
        provider_name: str = "openai_compatible",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.proxy = proxy
        self.extra_headers = extra_headers or {}
        self.provider_name = provider_name

    def complete(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        messages = [{"role": "system", "content": system}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user})

        client = _http_client(self.timeout, self.proxy)
        try:
            _log_request(
                self.provider_name,
                "POST",
                f"{self.base_url}/chat/completions",
                model=self.model,
                key_present=bool(self.api_key),
            )
            response = _post_with_retries(
                client,
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    **self.extra_headers,
                },
                json_body={"model": self.model, "messages": messages},
            )
            _log_response(self.provider_name, response)
        finally:
            client.close()

        if response.status_code in (401, 403):
            raise AIError(
                f"provider rejected the API key (HTTP {response.status_code}): "
                f"{_snippet(response.text)}"
            )
        if response.status_code == 429:
            raise AIError("provider rate limit exceeded")
        if response.status_code != 200:
            raise AIError(
                f"provider error ({response.status_code}): {_snippet(response.text)}"
            )
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as error:
            raise AIError(f"unexpected provider response: {error}") from None


_provider: LLMProvider | None = None


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
# Fast, cheap, strong multilingual (Persian) support, large context window —
# a good fit for grounded clinical Q&A.
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Free model for the initial OpenRouter integration test.
OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-r1:free"


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter (https://openrouter.ai) — an OpenAI-compatible aggregator.

    Same chat/completions wire format as the parent; only the base URL,
    the ``X-Title`` identification header, and the API-key source differ.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        proxy: str | None = None,
    ):
        super().__init__(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            model=model,
            timeout=timeout,
            proxy=proxy,
            extra_headers={"X-Title": "Clinical AI Copilot"},
            provider_name="openrouter",
        )


class GeminiProvider:
    """Native Google Gemini API client (``models/{model}:generateContent``).

    Maps the shared ``complete(system, user, history)`` interface onto
    Gemini's roles: system → ``system_instruction``, ``assistant`` history
    turns → ``model``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        proxy: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.proxy = proxy

    def complete(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        contents = []
        for turn in history or []:
            role = "model" if turn.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": turn["content"]}]})
        contents.append({"role": "user", "parts": [{"text": user}]})

        client = _http_client(self.timeout, self.proxy)
        try:
            _log_request(
                "gemini",
                "POST",
                f"{GEMINI_BASE_URL}/models/{self.model}:generateContent",
                model=self.model,
                key_present=bool(self.api_key),
            )
            response = _post_with_retries(
                client,
                f"{GEMINI_BASE_URL}/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json_body={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": contents,
                },
            )
            _log_response("gemini", response)
        finally:
            client.close()

        body_text = response.text
        json_body = _looks_like_json(response, body_text)

        if response.status_code == 400 and "API key not valid" in body_text:
            raise AIError(
                f"provider rejected the API key (HTTP 400): {_snippet(body_text)}"
            )
        if response.status_code == 403 and not json_body:
            # Google's edge answers restricted regions with an HTML 403 page
            # — this is a network/region block, NOT an API-key problem.
            raise AIError(
                "Google blocked the request at the network level "
                "(HTTP 403, HTML error page — typically a region restriction "
                "or filtering; route the backend through a proxy via AI_PROXY "
                "in .env and restart)"
            )
        if response.status_code in (401, 403):
            raise AIError(
                f"provider rejected the API key (HTTP {response.status_code}): "
                f"{_snippet(body_text)}"
            )
        if response.status_code == 429:
            raise AIError("provider rate limit exceeded")
        if response.status_code != 200:
            raise AIError(
                f"provider error ({response.status_code}): {_snippet(body_text)}"
            )
        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, ValueError) as error:
            raise AIError(f"unexpected provider response: {error}") from None


# Known provider ids (validated for runtime selection from the frontend).
PROVIDER_IDS = ("gemini", "openrouter", "openai_compatible")

_PROVIDER_DEFAULT_MODELS = {
    "gemini": GEMINI_DEFAULT_MODEL,
    "openrouter": OPENROUTER_DEFAULT_MODEL,
    "openai_compatible": OPENAI_DEFAULT_MODEL,
}


def _key_for(provider_id: str, settings) -> str:
    """Resolve the API key for a provider (dedicated var, AI_API_KEY fallback)."""
    if provider_id == "openrouter":
        return settings.OPENROUTER_API_KEY or settings.AI_API_KEY
    return settings.AI_API_KEY


def build_provider(
    provider_id: str | None = None, model: str | None = None
) -> LLMProvider:
    """Centralized provider construction (single registry, no scattered ifs).

    ``provider_id``/``model`` fall back to the AI_PROVIDER / AI_MODEL
    environment defaults when omitted (backwards compatible). Only provider
    and model ids may be supplied by callers — never URLs or keys.
    """
    settings = get_settings()
    resolved_id = (provider_id or settings.AI_PROVIDER or "openai_compatible").lower()
    if resolved_id not in PROVIDER_IDS:
        raise AIInvalidSelectionError(f"unknown provider: {resolved_id!r}")

    resolved_model = model or settings.AI_MODEL or _PROVIDER_DEFAULT_MODELS[resolved_id]
    if not resolved_model or len(resolved_model) > 200:
        raise AIInvalidSelectionError(
            f"no model configured for provider {resolved_id!r}"
        )
    if "://" in resolved_model or " " in resolved_model:
        # model is an id, never a URL / free text from the client
        raise AIInvalidSelectionError("model must be a plain model id")

    api_key = _key_for(resolved_id, settings)
    if not api_key:
        raise AIUnavailableError(f"API key for provider {resolved_id!r} is not configured")
    proxy = settings.AI_PROXY or None

    if resolved_id == "gemini":
        return GeminiProvider(
            api_key=api_key, model=resolved_model,
            timeout=settings.AI_TIMEOUT_SECONDS, proxy=proxy,
        )
    if resolved_id == "openrouter":
        return OpenRouterProvider(
            api_key=api_key, model=resolved_model,
            timeout=settings.AI_TIMEOUT_SECONDS, proxy=proxy,
        )
    return OpenAICompatibleProvider(
        base_url=settings.AI_BASE_URL,
        api_key=api_key, model=resolved_model,
        timeout=settings.AI_TIMEOUT_SECONDS, proxy=proxy,
    )


def get_provider() -> LLMProvider:
    """Cached ENV-DEFAULT provider (callers with explicit selection use build_provider)."""
    global _provider
    if _provider is None:
        _provider = build_provider()
    return _provider


def reset_provider_cache() -> None:
    """Test helper: force re-creation from current settings."""
    global _provider
    _provider = None


def _trim_text(value: str | None, limit: int = _MAX_TEXT_FIELD_CHARS) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[:limit] + " …"


def build_user_message(context_dict: dict, question: str) -> str:
    """Serialize the patient context (with capped text fields) + the question."""
    trimmed = dict(context_dict)
    for document in trimmed.get("documents", []):
        document["extracted_text"] = _trim_text(document.get("extracted_text"))
    for voice_note in trimmed.get("voice_notes", []):
        voice_note["transcript"] = _trim_text(voice_note.get("transcript"))
    for note in trimmed.get("clinical_notes", []):
        note["content"] = _trim_text(note.get("content"))

    return (
        "Patient record (JSON):\n"
        + json.dumps(trimmed, ensure_ascii=False, default=str)
        + f"\n\nPhysician's question:\n{question}"
    )
