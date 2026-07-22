from fastapi import APIRouter

from app.agents.citation_generator import CitationGeneratorAgent
from app.models.schemas import CitationRequest
from app.services.cache import cached

router = APIRouter(prefix="/citations", tags=["citations"])

_CACHE_TTL_SECONDS = 1800


@router.post("/generate")
async def generate_citations(request: CitationRequest) -> dict:
    return await cached(
        "citations",
        {"pmids": request.pmids, "format": request.format},
        _CACHE_TTL_SECONDS,
        lambda: CitationGeneratorAgent().run(
            query=", ".join(request.pmids), context={"format": request.format, "pmids": request.pmids}
        ),
    )
