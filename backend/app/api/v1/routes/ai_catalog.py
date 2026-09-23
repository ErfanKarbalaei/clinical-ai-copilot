"""AI provider/model catalog endpoint (frontend discovery — no secrets)."""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_current_user
from app.models import User
from app.services import ai_catalog

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get(
    "/providers",
    summary="Available AI providers and models (ids only — never keys/URLs)",
    description=(
        "Returns every CONFIGURED provider with its discoverable models: "
        "Gemini (curated static list) and OpenRouter (public /v1/models). "
        "A provider whose key is missing or whose discovery fails is simply "
        "omitted — models are never fabricated. The frontend may pass the "
        "returned `provider`/`model` ids back with chat requests."
    ),
)
def list_ai_providers(current_user: User = Depends(get_current_user)) -> dict:
    return {"providers": ai_catalog.list_providers()}
