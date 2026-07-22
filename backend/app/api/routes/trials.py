from fastapi import APIRouter

from app.agents.clinical_trial_analyzer import ClinicalTrialAnalyzerAgent
from app.models.schemas import ClinicalTrialSearchRequest
from app.services.cache import cached

router = APIRouter(prefix="/trials", tags=["trials"])

_CACHE_TTL_SECONDS = 1800


@router.post("/search")
async def search_trials(request: ClinicalTrialSearchRequest) -> dict:
    return await cached(
        "trials",
        {"condition": request.condition, "phase": request.phase, "status": request.status},
        _CACHE_TTL_SECONDS,
        lambda: ClinicalTrialAnalyzerAgent().run(
            request.condition, {"phase": request.phase, "status": request.status}
        ),
    )
