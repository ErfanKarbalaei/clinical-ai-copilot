"""Clinical AI agent endpoint (API v1) — Task 17 spike.

A SEPARATE path from the Task-15 persistent chat: the agent picks
read-only MCP tools (question → tool selection → real data → answer) via
the existing Gemini provider. Nothing is persisted, and if any part of
the MCP/agent stack fails, the normal persistent chat keeps working
untouched.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import patient_from_id
from app.models import Patient
from app.services import agent, ai
from app.services.agent import MCPToolError, MCPUnavailableError

router = APIRouter(tags=["agent"])

logger = logging.getLogger(__name__)

AI_NOT_CONFIGURED_DETAIL = "سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."
AI_PROVIDER_ERROR_DETAIL = "پاسخ عامل هوشمند تولید نشد؛ کمی بعد دوباره تلاش کنید."
MCP_UNAVAILABLE_DETAIL = "سرویس ابزار عامل (MCP) در دسترس نیست؛ گفتگوی معمول همچنان فعال است."


class AgentChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000, description="پرسش پزشک")


class AgentChatResponse(BaseModel):
    patient_id: int
    question: str
    answer: str
    tools_used: list[dict]
    generated_at: datetime


@router.post(
    "/patients/{patient_id}/agent/chat",
    response_model=AgentChatResponse,
    summary="Ask the clinical AI agent (MCP tool access spike)",
    description=(
        "Stateless agent path (separate from the persistent chat): the "
        "existing AI provider selects read-only patient-record tools "
        "executed through the local MCP server, then answers grounded in "
        "the fetched real data. Nothing is persisted; tool names are "
        "reported for transparency. The patient is always scoped by the "
        "backend — the model never supplies patient ids."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"},
        status.HTTP_502_BAD_GATEWAY: {"description": AI_PROVIDER_ERROR_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": MCP_UNAVAILABLE_DETAIL + " / " + AI_NOT_CONFIGURED_DETAIL
        },
    },
)
def agent_chat(
    patient_id: int,
    payload: AgentChatRequest,
    patient: Patient = Depends(patient_from_id),
) -> AgentChatResponse:
    try:
        result = agent.run_agent(patient=patient, question=payload.content.strip())
    except ai.AIUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_NOT_CONFIGURED_DETAIL,
        ) from None
    except MCPUnavailableError as error:
        logger.error("MCP unavailable (patient=%s): %s", patient.id, error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MCP_UNAVAILABLE_DETAIL,
        ) from None
    except (ai.AIError, MCPToolError) as error:
        logger.error(
            "agent failure (patient=%s): %s: %s",
            patient.id, type(error).__name__, error,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_PROVIDER_ERROR_DETAIL,
        ) from None

    return AgentChatResponse(
        patient_id=patient.id,
        question=payload.content.strip(),
        answer=result["answer"],
        tools_used=result["tools_used"],
        generated_at=datetime.now(timezone.utc),
    )
