"""Provider-agnostic LLM access for the clinical AI assistant.

Two boring implementations behind one tiny interface (``LLMProvider``):

- ``OpenAICompatibleProvider`` — any OpenAI-style ``chat/completions`` API
  (OpenAI, OpenRouter, Azure-style gateways, local Ollama/vLLM/LM Studio)
- ``GeminiProvider`` — Google's native ``generateContent`` API (v1beta)

Switching providers is pure configuration: ``AI_PROVIDER`` selects the
implementation, ``AI_MODEL`` is optional (empty = provider default).
No SDK dependency (plain httpx), no RAG, no vector search — just prompt +
patient context. The provider instance is created lazily and cached; tests
swap it by monkeypatching :func:`get_provider`.
"""

import json
import logging
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """The AI provider failed or rejected the request."""


class AIUnavailableError(AIError):
    """No AI provider configured (empty AI_API_KEY)."""


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


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions client (httpx, no SDK)."""

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

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

        client = httpx.Client(timeout=httpx.Timeout(self.timeout))
        try:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages},
            )
        except httpx.HTTPError as error:
            raise AIError(f"provider unreachable: {error}") from None
        finally:
            client.close()

        if response.status_code in (401, 403):
            raise AIError("provider rejected the API key")
        if response.status_code == 429:
            raise AIError("provider rate limit exceeded")
        if response.status_code != 200:
            raise AIError(
                f"provider error ({response.status_code}): {response.text[:200]}"
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
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider:
    """Native Google Gemini API client (``models/{model}:generateContent``).

    Maps the shared ``complete(system, user, history)`` interface onto
    Gemini's roles: system → ``system_instruction``, ``assistant`` history
    turns → ``model``.
    """

    def __init__(self, *, api_key: str, model: str, timeout: float):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

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

        client = httpx.Client(timeout=httpx.Timeout(self.timeout))
        try:
            response = client.post(
                f"{GEMINI_BASE_URL}/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": contents,
                },
            )
        except httpx.HTTPError as error:
            raise AIError(f"provider unreachable: {error}") from None
        finally:
            client.close()

        body_text = response.text
        if response.status_code in (401, 403) or (
            response.status_code == 400 and "API key not valid" in body_text
        ):
            raise AIError("provider rejected the API key")
        if response.status_code == 429:
            raise AIError("provider rate limit exceeded")
        if response.status_code != 200:
            raise AIError(
                f"provider error ({response.status_code}): {body_text[:200]}"
            )
        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, ValueError) as error:
            raise AIError(f"unexpected provider response: {error}") from None


def get_provider() -> LLMProvider:
    """Cached provider built from settings (dispatched by AI_PROVIDER)."""
    global _provider
    if _provider is None:
        settings = get_settings()
        if not settings.AI_API_KEY:
            raise AIUnavailableError("AI_API_KEY is not configured")
        if settings.AI_PROVIDER == "gemini":
            _provider = GeminiProvider(
                api_key=settings.AI_API_KEY,
                model=settings.AI_MODEL or GEMINI_DEFAULT_MODEL,
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        else:
            _provider = OpenAICompatibleProvider(
                base_url=settings.AI_BASE_URL,
                api_key=settings.AI_API_KEY,
                model=settings.AI_MODEL or OPENAI_DEFAULT_MODEL,
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
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
