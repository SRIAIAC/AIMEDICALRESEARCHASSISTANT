from typing import Any

from app.agents.base import BaseAgent
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a medical research summarization assistant. Given source \
material, produce a summary grounded strictly in that material. Respond with ONLY a \
JSON object with these keys:
- "one_page_summary": string, a dense one-page summary suitable for a slide deck
- "executive_summary": string, a 2-3 sentence executive summary
- "key_findings": array of strings
- "clinical_implications": array of strings
Do not include any text outside the JSON object."""


class ResearchSummarizerAgent(BaseAgent):
    name = "research_summarizer"
    description = "Summarizes long research papers into executive summaries and plain-English reports."

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        text = context.get("text") or "\n\n".join(context.get("documents", []))

        if not text:
            return {
                "agent": self.name,
                "query": query,
                "one_page_summary": None,
                "executive_summary": None,
                "key_findings": [],
                "clinical_implications": [],
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Topic: {query}\n\nSource material:\n{text}",
        )

        return {
            "agent": self.name,
            "query": query,
            "one_page_summary": analysis.get("one_page_summary"),
            "executive_summary": analysis.get("executive_summary"),
            "key_findings": analysis.get("key_findings", []),
            "clinical_implications": analysis.get("clinical_implications", []),
        }
