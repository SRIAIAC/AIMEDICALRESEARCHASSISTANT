from typing import Any

from app.agents.base import BaseAgent
from app.services.embeddings import Embedder, get_embedder
from app.services.external_apis import PubMedClient, get_pubmed_client
from app.services.llm import LLMClient, get_llm_client
from app.services.vector_store import VectorStore, get_vector_store

SYSTEM_PROMPT = """You are a biomedical literature review assistant. Given a research \
topic and a set of PubMed abstracts, produce a systematic review grounded strictly in \
the provided abstracts. Respond with ONLY a JSON object with these keys:
- "summary": string, a concise narrative summary of the literature
- "key_findings": array of strings, the most important findings across studies
- "evidence_level": string, an overall GRADE-style rating (e.g. "High", "Moderate", "Low", "Very Low")
- "conclusions": array of strings, the main conclusions and any research gaps or conflicting results
Do not include any text outside the JSON object."""


class LiteratureReviewAgent(BaseAgent):
    name = "literature_review"
    description = "Searches PubMed/PMC, extracts findings, and produces systematic literature reviews."

    def __init__(
        self,
        pubmed_client: PubMedClient | None = None,
        vector_store: VectorStore | None = None,
        embedder: Embedder | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._pubmed = pubmed_client or get_pubmed_client()
        self._vector_store = vector_store or get_vector_store()
        self._embedder = embedder or get_embedder()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        max_results = (context or {}).get("max_results", 20)
        pmids = await self._pubmed.search(query, max_results=max_results)
        if not pmids:
            return self._empty_result(query)

        summaries = await self._pubmed.fetch_summaries(pmids)
        abstracts = await self._pubmed.fetch_abstracts(pmids)

        references = [PubMedClient.to_reference(summary) for summary in summaries]
        documents = [f"{ref['title']}\n{abstracts.get(ref['pmid'], '')}" for ref in references]

        if documents:
            self._vector_store.upsert(
                ids=[ref["pmid"] for ref in references],
                embeddings=self._embedder.embed(documents),
                metadatas=[
                    {
                        "source": "pubmed",
                        "pmid": ref["pmid"],
                        "title": ref["title"],
                        "journal": ref["journal"],
                        "year": ref["year"],
                        "text": document,
                    }
                    for ref, document in zip(references, documents)
                ],
            )

        context_text = "\n\n".join(
            f"[{ref['pmid']}] {ref['title']} ({ref['year']})\n{abstracts.get(ref['pmid'], '')}" for ref in references
        )
        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Research topic: {query}\n\nSource abstracts:\n{context_text}",
        )

        return {
            "agent": self.name,
            "query": query,
            "summary": analysis.get("summary"),
            "key_findings": analysis.get("key_findings", []),
            "evidence_level": analysis.get("evidence_level"),
            "conclusions": analysis.get("conclusions", []),
            "sources": [
                {
                    "pmid": ref["pmid"],
                    "title": ref["title"],
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{ref['pmid']}/",
                }
                for ref in references
            ],
        }

    def _empty_result(self, query: str) -> dict[str, Any]:
        return {
            "agent": self.name,
            "query": query,
            "summary": None,
            "key_findings": [],
            "evidence_level": None,
            "conclusions": [],
            "sources": [],
        }
