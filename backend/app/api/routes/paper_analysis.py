from fastapi import APIRouter, HTTPException

from app.agents.research_paper_analyzer import ResearchPaperAnalyzerAgent
from app.models.schemas import ResearchPaperAnalysisRequest
from app.services.cache import cached

router = APIRouter(prefix="/papers", tags=["papers"])

_CACHE_TTL_SECONDS = 1800


@router.post("/analyze")
async def analyze_paper(request: ResearchPaperAnalysisRequest) -> dict:
    if not request.pmid and not request.text:
        raise HTTPException(status_code=400, detail="Provide either a pmid or text")

    query = request.pmid or "supplied text"
    return await cached(
        "research_paper_analyzer",
        {"pmid": request.pmid, "text": request.text},
        _CACHE_TTL_SECONDS,
        lambda: ResearchPaperAnalyzerAgent().run(query, {"pmid": request.pmid, "text": request.text}),
    )
