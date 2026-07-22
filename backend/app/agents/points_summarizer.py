from typing import Any

from app.agents.base import BaseAgent
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a summarization assistant. Given a block of text, summarize it \
as a clean bulleted list — NOT prose paragraphs. Every point must be a self-contained, \
concise statement grounded in the supplied text; do not add outside information. Respond \
with ONLY a JSON object with these keys:
- "title": string, a short title for what's being summarized
- "points": array of strings, the summary as discrete bullet points (aim for 4-8 points —
  fewer if the text is short, more only if genuinely needed)
- "key_takeaway": string, the single most important point, one sentence
Do not include any text outside the JSON object."""


class PointsSummarizerAgent(BaseAgent):
    """Distinct from ResearchSummarizerAgent (which produces prose:
    one-page/executive summaries) — this always returns a bulleted list,
    for quick point-form summaries usable from anywhere in the app.
    """

    name = "points_summarizer"
    description = "Summarizes supplied text as a bulleted list of points."

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        text = (context or {}).get("text", "")
        if not text.strip():
            return {
                "agent": self.name,
                "query": query,
                "title": None,
                "points": [],
                "key_takeaway": None,
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Topic (optional context): {query}\n\nText to summarize:\n{text}",
        )

        return {
            "agent": self.name,
            "query": query,
            "title": analysis.get("title"),
            "points": analysis.get("points", []),
            "key_takeaway": analysis.get("key_takeaway"),
        }
