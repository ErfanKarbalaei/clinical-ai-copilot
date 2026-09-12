"""Direct Gemini connection test — no frontend, no database, no patient context.

Sends exactly one tiny prompt ("سلام، فقط بنویس تست موفق بود.") straight to
the configured provider and prints everything needed to diagnose a failure.
Never prints the API key itself.

Run:  python -m scripts.direct_gemini_test
"""

import logging
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.core.config import get_settings  # noqa: E402
from app.services import ai  # noqa: E402
from app.services.ai import AIError, GeminiProvider  # noqa: E402

# Make the provider's [ai-request]/[ai-response] debug logs visible here.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(levelname)-8s | %(name)s | %(message)s",
    encoding="utf-8",
)

TEST_PROMPT = "سلام، فقط بنویس تست موفق بود."


def main() -> None:
    settings = get_settings()
    print("=" * 70)
    print("AI configuration")
    print(f"  AI_PROVIDER : {settings.AI_PROVIDER}")
    print(
        f"  AI_MODEL    : {settings.AI_MODEL or '(empty → provider default)'}"
    )
    print(f"  AI_BASE_URL : {settings.AI_BASE_URL} (only used by openai_compatible)")
    print(f"  AI_PROXY    : {settings.AI_PROXY or '(none — direct connection)'}")
    print(f"  AI_API_KEY present: {bool(settings.AI_API_KEY)} (value never shown)")
    print("=" * 70)

    try:
        provider = ai.get_provider()
    except AIError as error:
        print(f"PROVIDER NOT CONFIGURED: {error}")
        print("→ cause: (B) API key missing")
        raise SystemExit(1)

    model = getattr(provider, "model", "?")
    url = f"{ai.GEMINI_BASE_URL}/models/{model}:generateContent"
    print(f"provider class : {type(provider).__name__}")
    print(f"resolved model : {model}")
    print(f"endpoint       : {url}")
    print(f"method         : POST   auth header: x-goog-api-key (sent, value hidden)")
    print("=" * 70)
    print(f"Sending test prompt: {TEST_PROMPT!r}")
    print("=" * 70)

    try:
        answer = provider.complete(
            system="You are a connection test. Reply exactly as instructed.",
            user=TEST_PROMPT,
        )
    except AIError as error:
        print()
        print("GEMINI CONNECTION FAILED")
        print(f"  error type : AIError")
        print(f"  message    : {error}")
        print("-" * 70)
        message = str(error)
        if "network level" in message:
            print("  classification: (F) network/region block — Google's edge returns")
            print("  an HTML 403 page before the API evaluates the key. The request")
            print("  format is correct; this machine's network cannot reach the")
            print("  Generative Language API directly.")
        elif "rejected the API key" in message:
            print("  classification: (A) API key invalid")
        elif "rate limit" in message:
            print("  classification: (E) quota/rate limit")
        elif "unreachable" in message:
            print("  classification: (F) network/DNS/SSL/timeout")
        raise SystemExit(2)

    print()
    print("GEMINI CONNECTION OK")
    print(f"  answer: {answer.strip()}")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
