from fastapi import APIRouter

from app.agents.research_summarizer import ResearchSummarizerAgent
from app.models.schemas import SummarizeRequest
from app.services.cache import cached

router = APIRouter(prefix="/summarize", tags=["summarize"])

_CACHE_TTL_SECONDS = 1800


@router.post("")
async def summarize_text(request: SummarizeRequest) -> dict:
    return await cached(
        "summarize",
        {"query": request.query, "text": request.text},
        _CACHE_TTL_SECONDS,
        lambda: ResearchSummarizerAgent().run(request.query, {"text": request.text}),
    )
