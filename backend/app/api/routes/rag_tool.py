from fastapi import APIRouter

from app.agents.points_summarizer import PointsSummarizerAgent
from app.agents.web_search_rag import WebSearchRAGAgent
from app.models.schemas import PointsSummarizeRequest, WebSearchRAGRequest
from app.services.cache import cached

router = APIRouter(prefix="/rag", tags=["rag"])

_CACHE_TTL_SECONDS = 1800


@router.post("/websearch")
async def web_search_rag(request: WebSearchRAGRequest) -> dict:
    return await cached(
        "web_search_rag",
        {"query": request.query, "limit": request.limit},
        _CACHE_TTL_SECONDS,
        lambda: WebSearchRAGAgent().run(request.query, {"limit": request.limit}),
    )


@router.post("/summarize-points")
async def summarize_points(request: PointsSummarizeRequest) -> dict:
    return await cached(
        "points_summarizer",
        {"text": request.text, "topic": request.topic},
        _CACHE_TTL_SECONDS,
        lambda: PointsSummarizerAgent().run(request.topic, {"text": request.text}),
    )
