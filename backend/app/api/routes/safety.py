from fastapi import APIRouter

from app.agents.safety import SafetyAgent
from app.models.schemas import SafetyRequest
from app.services.cache import cached

router = APIRouter(prefix="/safety", tags=["safety"])

_CACHE_TTL_SECONDS = 1800


@router.post("/check")
async def check_safety(request: SafetyRequest) -> dict:
    return await cached(
        "safety",
        {"drug_name": request.drug_name},
        _CACHE_TTL_SECONDS,
        lambda: SafetyAgent().run(request.drug_name),
    )
