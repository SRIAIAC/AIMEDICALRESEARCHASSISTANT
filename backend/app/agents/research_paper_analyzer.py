from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import PubMedClient, get_pubmed_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a medical research paper analysis assistant. Given the text of a \
research paper (a title and abstract, or full text), extract its structural elements \
grounded strictly in the provided text. If a field genuinely isn't discernible from the \
text, use null (or an empty array) rather than guessing or inventing detail. Respond with \
ONLY a JSON object with these keys:
- "objectives": string or null, the stated research objective/aim
- "methodology": string or null, the study design and methods used
- "patient_population": string or null, who was studied (sample size, demographics, criteria)
- "interventions": array of strings, interventions/treatments studied
- "endpoints": array of strings, primary/secondary endpoints or outcome measures
- "results": string or null, the key results
- "statistical_findings": array of strings, specific statistics mentioned (p-values,
  confidence intervals, effect sizes, hazard ratios, etc.)
- "limitations": array of strings, stated or apparent limitations
- "conclusions": string or null, the paper's stated conclusions
Do not include any text outside the JSON object."""


class ResearchPaperAnalyzerAgent(BaseAgent):
    """Structured single-paper extraction — distinct from Literature Review,
    which synthesizes across many papers. Accepts either a PMID (fetched
    from PubMed) or raw text (e.g. from an uploaded document), so it can
    analyze a paper that isn't on PubMed at all.
    """

    name = "research_paper_analyzer"
    description = "Extracts objectives, methodology, population, endpoints, results, and limitations from a single paper."

    def __init__(self, pubmed_client: PubMedClient | None = None, llm_client: LLMClient | None = None) -> None:
        self._pubmed = pubmed_client or get_pubmed_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        pmid = context.get("pmid")
        text = context.get("text")
        title = query

        if not text and pmid:
            summaries = await self._pubmed.fetch_summaries([pmid])
            if summaries:
                title = summaries[0].get("title", query)
            abstracts = await self._pubmed.fetch_abstracts([pmid])
            text = abstracts.get(pmid, "")

        if not text:
            return self._empty_result(query, title)

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Title: {title}\n\nPaper text:\n{text}",
        )

        return {
            "agent": self.name,
            "query": query,
            "title": title,
            "objectives": analysis.get("objectives"),
            "methodology": analysis.get("methodology"),
            "patient_population": analysis.get("patient_population"),
            "interventions": analysis.get("interventions", []),
            "endpoints": analysis.get("endpoints", []),
            "results": analysis.get("results"),
            "statistical_findings": analysis.get("statistical_findings", []),
            "limitations": analysis.get("limitations", []),
            "conclusions": analysis.get("conclusions"),
        }

    def _empty_result(self, query: str, title: str) -> dict[str, Any]:
        return {
            "agent": self.name,
            "query": query,
            "title": title,
            "objectives": None,
            "methodology": None,
            "patient_population": None,
            "interventions": [],
            "endpoints": [],
            "results": None,
            "statistical_findings": [],
            "limitations": [],
            "conclusions": None,
        }
