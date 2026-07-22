from fastapi import APIRouter

from app.agents.orchestrator import ResearchPlanner
from app.models.schemas import ResearchQueryRequest, ResearchReportResponse
from app.services.cache import cached

router = APIRouter(prefix="/research", tags=["research"])

_CACHE_TTL_SECONDS = 1800


@router.post("", response_model=ResearchReportResponse)
async def run_research(request: ResearchQueryRequest) -> ResearchReportResponse:
    report = await cached(
        "research",
        {"query": request.query, "context": request.context},
        _CACHE_TTL_SECONDS,
        lambda: ResearchPlanner().run(request.query, request.context),
    )
    return ResearchReportResponse(**report)
