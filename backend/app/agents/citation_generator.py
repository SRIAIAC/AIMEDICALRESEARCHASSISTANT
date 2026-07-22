from typing import Any

from app.agents.base import BaseAgent
from app.services.citations import Reference, build_bibliography
from app.services.external_apis import PubMedClient, get_pubmed_client


class CitationGeneratorAgent(BaseAgent):
    name = "citation_generator"
    description = "Collects references, dedupes citations, and generates bibliographies in multiple formats."

    def __init__(self, pubmed_client: PubMedClient | None = None) -> None:
        self._pubmed = pubmed_client or get_pubmed_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        citation_format = context.get("format", "APA")
        references: list[Reference] | None = context.get("references")

        if references is None:
            pmids = context.get("pmids") or [p.strip() for p in query.split(",") if p.strip()]
            summaries = await self._pubmed.fetch_summaries(pmids)
            references = [PubMedClient.to_reference(summary) for summary in summaries]

        result = build_bibliography(references, citation_format)

        return {
            "agent": self.name,
            "query": query,
            "format": citation_format,
            **result,
        }
