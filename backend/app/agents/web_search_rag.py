from typing import Any

from app.agents.base import BaseAgent
from app.services.llm import LLMClient, get_llm_client
from app.services.web_search import WebSearchClient, get_web_search_client

SYSTEM_PROMPT = """You are a research assistant answering a question using web search \
results (from Wikipedia and, when available, DuckDuckGo). Answer using ONLY the provided \
excerpts — do not use outside knowledge. If the excerpts don't contain enough information, \
say so explicitly rather than guessing. Respond with ONLY a JSON object with these keys:
- "answer": string, a short grounded answer to the question
- "key_points": array of strings, the supporting facts as concise, self-contained bullet
  points — each one traceable to a specific excerpt
- "supporting_sources": array of strings, the titles of the sources that back the answer
- "confidence": string, one of "high", "medium", "low" reflecting how well the excerpts
  support the answer
Do not include any text outside the JSON object."""


class WebSearchRAGAgent(BaseAgent):
    """RAG over live web search results (Wikipedia + DuckDuckGo) rather
    than the local vector store — see DocumentQAAgent for the
    uploaded-documents/PubMed-abstracts version of this pattern.
    """

    name = "web_search_rag"
    description = "Answers a question using retrieval-augmented generation over web search results."

    def __init__(
        self,
        web_search_client: WebSearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._web_search = web_search_client or get_web_search_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        limit = (context or {}).get("limit", 5)
        results = await self._web_search.search(query, limit=limit)
        results = [r for r in results if r.get("snippet")]

        if not results:
            return {
                "agent": self.name,
                "query": query,
                "answer": None,
                "key_points": [],
                "supporting_sources": [],
                "confidence": None,
                "sources": [],
            }

        excerpt_blocks = [f"[{r['title']}]\n{r['snippet']}" for r in results]
        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Question: {query}\n\nWeb search excerpts:\n\n" + "\n\n".join(excerpt_blocks),
        )

        return {
            "agent": self.name,
            "query": query,
            "answer": analysis.get("answer"),
            "key_points": analysis.get("key_points", []),
            "supporting_sources": analysis.get("supporting_sources", []),
            "confidence": analysis.get("confidence"),
            "sources": [{"title": r["title"], "url": r["url"], "source": r["source"]} for r in results],
        }
