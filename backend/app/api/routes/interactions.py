from fastapi import APIRouter

from app.agents.drug_interaction import DrugInteractionAgent
from app.models.schemas import DrugInteractionRequest
from app.services.cache import cached

router = APIRouter(prefix="/interactions", tags=["interactions"])

_CACHE_TTL_SECONDS = 1800


@router.post("/check")
async def check_interaction(request: DrugInteractionRequest) -> dict:
    return await cached(
        "drug_interaction",
        {"drug_a": request.drug_a, "drug_b": request.drug_b},
        _CACHE_TTL_SECONDS,
        lambda: DrugInteractionAgent().run(
            request.drug_a, {"drug_a": request.drug_a, "drug_b": request.drug_b}
        ),
    )
