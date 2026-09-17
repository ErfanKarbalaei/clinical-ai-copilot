"""Clinical AI agent adapter (Task 17 spike).

Orchestrates: question → Gemini (existing provider) picks read-only MCP
tools → the tools fetch REAL patient data through the local MCP server →
Gemini writes the final grounded answer.

Boundaries (kept strictly):
- AI  = reasoning / tool selection / final answer
- MCP = controlled read-only tool interface (this repo's app.mcp_server)
- Backend = security, validation, persistence (unchanged, still the owner)
- DB = source of truth · Storage = source of original files (never here)

The agent never lets the model choose a patient: tool names come from the
model, but ``patient_id`` is ALWAYS injected server-side from the scoped
route. Text-JSON planning is used instead of native function calling so
``services/ai.py`` stays completely untouched.
"""

import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

from app.models import Patient
from app.services import ai

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Tool surface (must match app.mcp_server.TOOL_NAMES) + Persian labels.
TOOL_LABELS: dict[str, str] = {
    "get_patient": "مشخصات بیمار",
    "get_patient_context": "پروندهٔ کامل بیمار",
    "get_patient_labs": "آزمایش‌های بیمار",
    "get_patient_medications": "داروهای بیمار",
    "get_patient_documents": "اسناد بیمار",
    "get_patient_timeline": "تایم‌لاین بیمار",
}
MAX_TOOLS_PER_QUESTION = 3
_MAX_TOOL_RESULT_CHARS = 4000


class MCPUnavailableError(Exception):
    """The local MCP server could not be started / is not reachable."""


class MCPToolError(Exception):
    """A tool call failed (e.g. unknown patient) — no data is fabricated."""


# ---------------------------------------------------------------------------
# MCP stdio client: one persistent subprocess session on a background loop
# (the FastAPI routes are sync; the SDK client session is async).
# ---------------------------------------------------------------------------


class MCPStdioClient:
    """Persistent stdio client for the local read-only MCP server."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, daemon=True, name="mcp-client-loop"
        )
        self._thread.start()
        self._session = None
        self._session_cm = None
        self._transport_cm = None
        self._lock = threading.Lock()

    def _submit(self, coro, timeout: float) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def ensure_session(self) -> None:
        with self._lock:
            if self._session is not None:
                return
            try:
                self._submit(self._open(), timeout=30)
            except Exception as error:
                self._session = None
                raise MCPUnavailableError(
                    f"could not start local MCP server: {type(error).__name__}: {error}"
                ) from None
            logger.info("MCP session ready (tools: %s)", sorted(TOOL_LABELS))

    async def _open(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            cwd=str(BACKEND_DIR),
        )
        self._transport_cm = stdio_client(params)
        read, write = await self._transport_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    def list_tools(self) -> list[str]:
        self.ensure_session()
        result = self._submit(self._session.list_tools(), timeout=30)
        return [tool.name for tool in result.tools]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.ensure_session()
        started = time.monotonic()
        try:
            result = self._submit(
                self._session.call_tool(name, arguments), timeout=60
            )
        except MCPUnavailableError:
            raise
        except Exception as error:
            self._reset()  # broken pipe / dead subprocess → force reconnect
            raise MCPToolError(f"tool {name} failed: {error}") from None
        logger.info(
            "mcp tool %s done in %.2fs", name, time.monotonic() - started
        )
        if getattr(result, "is_error", False):
            message = ""
            for block in getattr(result, "content", []) or []:
                text = getattr(block, "text", None)
                if text:
                    message = text
                    break
            raise MCPToolError(f"tool {name}: {message or 'tool error'}")
        return self._result_data(result)

    @staticmethod
    def _result_data(result: Any) -> Any:
        structured = getattr(result, "structured_content", None)
        if structured is None:
            # fall back to the text payload if structured output is absent
            text = ""
            for block in getattr(result, "content", []) or []:
                piece = getattr(block, "text", None)
                if piece:
                    text = piece
                    break
            try:
                structured = json.loads(text)
            except (ValueError, TypeError):
                return text
        # SDK v2 wraps non-object returns (e.g. lists) in {"result": ...}
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured

    def _reset(self) -> None:
        self._session = None
        self._session_cm = None
        self._transport_cm = None

    def close(self) -> None:
        with self._lock:
            if self._session_cm is not None:
                try:
                    self._submit(
                        self._session_cm.__aexit__(None, None, None), timeout=10
                    )
                except Exception:  # noqa: BLE001 — best-effort teardown
                    pass
            if self._transport_cm is not None:
                try:
                    self._submit(
                        self._transport_cm.__aexit__(None, None, None), timeout=10
                    )
                except Exception:  # noqa: BLE001
                    pass
            self._reset()


_client: MCPStdioClient | None = None


def get_mcp_client() -> MCPStdioClient:
    """Cached local MCP client (tests swap this via monkeypatch)."""
    global _client
    if _client is None:
        _client = MCPStdioClient()
    return _client


def reset_mcp_client() -> None:
    """Test helper: drop the cached client."""
    global _client
    if _client is not None:
        _client.close()
    _client = None


# ---------------------------------------------------------------------------
# Agent: plan (which tools) → fetch via MCP → answer with real data
# ---------------------------------------------------------------------------

AGENT_PLANNER_PROMPT = f"""You are the planning step of a clinical AI agent used by a physician.
You receive one physician question about ONE known patient. You may either
answer directly (general knowledge only) or request read-only patient-record
tools to ground the answer in the real record.

Available tools (exact names):
{chr(10).join(f"- {name}" for name in sorted(TOOL_LABELS))}

Rules:
- For anything patient-specific, request the MOST RELEVANT tool(s) — 1 to
  {MAX_TOOLS_PER_QUESTION} tools. Prefer the narrow tool over the full context:
  medications → get_patient_medications, labs → get_patient_labs,
  documents → get_patient_documents, general/combined status →
  get_patient_context (or a combination), history/events → get_patient_timeline.
- Only answer directly (no tools) for purely general questions.
- NEVER invent tool names. NEVER claim patient facts from memory.

Reply with ONLY a JSON object, no markdown fences, no extra text:
{{"tools": ["<tool-name>", ...]}}
or
{{"answer": "<direct Persian answer>"}}
"""

_AGENT_ANSWER_ADDENDUM = """

Agent context rules:
- The data below was fetched from the patient's REAL record through
  read-only tools. Ground every patient-specific statement in it.
- If a tool result is empty, state plainly that the record contains no
  such data — never guess or fabricate values.
"""


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1 :] if first_newline != -1 else ""
    cleaned = cleaned.replace("```", "")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ai.AIError("agent plan contained no JSON object")
    try:
        data = json.loads(cleaned[start : end + 1])
    except ValueError as error:
        raise ai.AIError(f"malformed agent plan: {error}") from None
    if not isinstance(data, dict):
        raise ai.AIError("agent plan is not a JSON object")
    return data


def run_agent(*, patient: Patient, question: str) -> dict[str, Any]:
    """Two Gemini calls over the EXISTING provider + MCP tool execution.

    Returns {"answer": str, "tools_used": [{"name", "label"}]}.
    Never fabricates data: MCP/tool failures raise; the route maps them.
    """
    logger.info(
        "agent started (patient=%s, question=%d chars)", patient.id, len(question)
    )
    provider = ai.get_provider()  # raises AIUnavailableError (→ 503)

    # 1) planning call — which read-only tools does this question need?
    logger.info("gemini planner call started")
    plan_raw = provider.complete(
        system=AGENT_PLANNER_PROMPT,
        user=(
            f"Patient: {patient.first_name} {patient.last_name} (id {patient.id})\n"
            f"Physician's question:\n{question}"
        ),
    )
    logger.info("gemini planner call completed")
    plan = _extract_json_object(plan_raw)

    direct_answer = plan.get("answer")
    if isinstance(direct_answer, str) and direct_answer.strip() and not plan.get("tools"):
        logger.info("agent completed without tools (direct answer)")
        return {"answer": direct_answer.strip(), "tools_used": []}

    requested = [
        name
        for name in plan.get("tools", [])
        if isinstance(name, str) and name in TOOL_LABELS
    ]
    if plan.get("tools") and not requested:
        logger.warning(
            "agent plan requested unknown tools: %s — falling back to context",
            plan.get("tools"),
        )
    if not requested:
        requested = ["get_patient_context"]  # safe default for patient questions

    tool_results: dict[str, Any] = {}
    for name in list(dict.fromkeys(requested))[:MAX_TOOLS_PER_QUESTION]:
        logger.info("tool selected: %s", name)
        logger.info("tool call started: %s", name)
        # SECURITY: the model never supplies ids — the scoped patient is
        # always injected server-side by the backend.
        data = get_mcp_client().call_tool(name, {"patient_id": patient.id})
        serialized = json.dumps(data, ensure_ascii=False, default=str)
        if len(serialized) > _MAX_TOOL_RESULT_CHARS:
            serialized = serialized[:_MAX_TOOL_RESULT_CHARS] + " …[بریده شد]"
        tool_results[name] = serialized
        logger.info("tool call completed: %s", name)

    # 2) answering call — same grounding rules as the clinical chat
    logger.info("gemini answer call started")
    answer = provider.complete(
        system=ai.SYSTEM_PROMPT + _AGENT_ANSWER_ADDENDUM,
        user=(
            f"Physician's question:\n{question}\n\n"
            "Tool results from the patient's real record (JSON):\n"
            + json.dumps(tool_results, ensure_ascii=False)
        ),
    )
    logger.info("gemini answer call completed")
    logger.info("agent completed (patient=%s, tools=%s)", patient.id, list(tool_results))
    return {
        "answer": answer.strip(),
        "tools_used": [
            {"name": name, "label": TOOL_LABELS[name]} for name in tool_results
        ],
    }
