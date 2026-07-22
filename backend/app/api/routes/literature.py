from fastapi import APIRouter

from app.agents.literature_review import LiteratureReviewAgent
from app.models.schemas import LiteratureSearchRequest
from app.services.cache import cached

router = APIRouter(prefix="/literature", tags=["literature"])

_CACHE_TTL_SECONDS = 1800


@router.post("/search")
async def search_literature(request: LiteratureSearchRequest) -> dict:
    return await cached(
        "literature",
        {"topic": request.topic, "max_results": request.max_results},
        _CACHE_TTL_SECONDS,
        lambda: LiteratureReviewAgent().run(request.topic, {"max_results": request.max_results}),
    )
