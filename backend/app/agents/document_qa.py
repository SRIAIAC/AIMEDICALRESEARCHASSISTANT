from typing import Any

from app.agents.base import BaseAgent
from app.services.embeddings import Embedder, get_embedder
from app.services.llm import LLMClient, get_llm_client
from app.services.vector_store import VectorStore, get_vector_store

SYSTEM_PROMPT = """You are a medical document Q&A assistant using retrieval-augmented \
generation. Answer the user's question using ONLY the provided source excerpts — do not \
use outside knowledge. If the excerpts don't contain enough information to answer, say so \
explicitly rather than guessing. Every claim in your answer must be traceable to a specific \
source excerpt. Each excerpt is labeled "[id] label" — use only the id itself (without the \
square brackets) when citing it. Respond with ONLY a JSON object with these keys:
- "answer": string, the answer grounded in the provided excerpts (or a clear statement that
  the excerpts don't contain the answer)
- "supporting_sources": array of strings, the source ids (no brackets, exactly as given)
  that directly support the answer
- "confidence": string, one of "high", "medium", "low" reflecting how well the excerpts
  support the answer
Do not include any text outside the JSON object."""


class DocumentQAAgent(BaseAgent):
    """Retrieval-augmented Q&A over whatever is currently indexed in the
    vector store — uploaded PDF chunks and/or PubMed abstracts the
    Literature Review agent has indexed. Unlike a plain semantic search
    (`/documents/search`), this actually answers the question rather than
    just returning raw matches, and every claim is expected to cite which
    retrieved excerpt backs it.
    """

    name = "document_qa"
    description = "Answers questions using RAG over indexed documents and literature."

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._embedder = embedder or get_embedder()
        self._vector_store = vector_store or get_vector_store()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        top_k = (context or {}).get("top_k", 5)
        [embedding] = self._embedder.embed([query])
        matches = [m for m in self._vector_store.query(embedding, top_k=top_k) if m.get("text")]

        if not matches:
            return {
                "agent": self.name,
                "query": query,
                "answer": None,
                "supporting_sources": [],
                "confidence": None,
                "sources": [],
            }

        sources: list[dict[str, Any]] = []
        excerpt_blocks: list[str] = []
        for i, match in enumerate(matches):
            if match.get("pmid"):
                source_id = match["pmid"]
                label = match.get("title") or source_id
            elif match.get("doc_id"):
                source_id = f"{match['doc_id']}:{match.get('chunk_index', 0)}"
                label = match.get("filename") or source_id
            else:
                source_id = f"source-{i}"
                label = source_id

            sources.append(
                {
                    "id": source_id,
                    "label": label,
                    "source_type": match.get("source", "unknown"),
                    "excerpt": (match.get("text") or "")[:400],
                }
            )
            excerpt_blocks.append(f"[{source_id}] {label}\n{match.get('text', '')}")

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Question: {query}\n\nSource excerpts:\n\n" + "\n\n".join(excerpt_blocks),
        )

        # The model doesn't always follow the "no brackets" instruction
        # exactly, and callers match these against `sources[].id` verbatim
        # (e.g. to highlight cited sources in the UI), so strip defensively
        # rather than relying solely on the prompt.
        supporting_sources = [str(s).strip("[]") for s in analysis.get("supporting_sources", [])]

        return {
            "agent": self.name,
            "query": query,
            "answer": analysis.get("answer"),
            "supporting_sources": supporting_sources,
            "confidence": analysis.get("confidence"),
            "sources": sources,
        }
