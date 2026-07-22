from fastapi import APIRouter

from app.api.routes import (
    citations,
    comparative,
    documents,
    drugs,
    health,
    interactions,
    knowledge_graph,
    literature,
    news,
    paper_analysis,
    rag_tool,
    regulatory,
    research,
    safety,
    summarize,
    trials,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(research.router)
api_router.include_router(literature.router)
api_router.include_router(drugs.router)
api_router.include_router(trials.router)
api_router.include_router(citations.router)
api_router.include_router(summarize.router)
api_router.include_router(news.router)
api_router.include_router(documents.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(safety.router)
api_router.include_router(regulatory.router)
api_router.include_router(paper_analysis.router)
api_router.include_router(interactions.router)
api_router.include_router(comparative.router)
api_router.include_router(rag_tool.router)
