from fastapi import APIRouter

from app.agents.regulatory import RegulatoryAgent
from app.models.schemas import RegulatoryRequest
from app.services.cache import cached

router = APIRouter(prefix="/regulatory", tags=["regulatory"])

_CACHE_TTL_SECONDS = 1800


@router.post("/check")
async def check_regulatory(request: RegulatoryRequest) -> dict:
    return await cached(
        "regulatory",
        {"drug_name": request.drug_name},
        _CACHE_TTL_SECONDS,
        lambda: RegulatoryAgent().run(request.drug_name),
    )
