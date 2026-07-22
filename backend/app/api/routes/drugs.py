from fastapi import APIRouter

from app.agents.drug_discovery import DrugDiscoveryAgent
from app.models.schemas import DrugLookupRequest
from app.services.cache import cached

router = APIRouter(prefix="/drugs", tags=["drugs"])

_CACHE_TTL_SECONDS = 1800


@router.post("/lookup")
async def lookup_drug(request: DrugLookupRequest) -> dict:
    return await cached(
        "drugs",
        {"drug_name": request.drug_name},
        _CACHE_TTL_SECONDS,
        lambda: DrugDiscoveryAgent().run(request.drug_name),
    )
