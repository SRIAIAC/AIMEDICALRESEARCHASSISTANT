from fastapi import APIRouter

from app.agents.knowledge_graph import KnowledgeGraphAgent
from app.models.schemas import KnowledgeGraphRequest
from app.services.cache import cached

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])

_CACHE_TTL_SECONDS = 1800


@router.post("")
async def build_knowledge_graph(request: KnowledgeGraphRequest) -> dict:
    return await cached(
        "knowledge_graph",
        {"drug_name": request.drug_name},
        _CACHE_TTL_SECONDS,
        lambda: KnowledgeGraphAgent().run(request.drug_name),
    )
