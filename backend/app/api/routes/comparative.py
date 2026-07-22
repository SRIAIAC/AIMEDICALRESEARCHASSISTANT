from fastapi import APIRouter

from app.agents.comparative_analysis import ComparativeAnalysisAgent
from app.models.schemas import ComparativeAnalysisRequest
from app.services.cache import cached

router = APIRouter(prefix="/compare", tags=["compare"])

_CACHE_TTL_SECONDS = 1800


@router.post("/drugs")
async def compare_drugs(request: ComparativeAnalysisRequest) -> dict:
    query = " vs ".join(request.drug_names)
    return await cached(
        "comparative_analysis",
        {"drug_names": request.drug_names},
        _CACHE_TTL_SECONDS,
        lambda: ComparativeAnalysisAgent().run(query, {"drug_names": request.drug_names}),
    )
