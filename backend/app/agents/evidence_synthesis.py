import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are an evidence synthesis assistant for medical research. Given \
structured findings already gathered by several specialist research agents (literature \
review, drug intelligence, clinical trials, safety data, regulatory history), synthesize \
them into a single cross-cutting evidence assessment. Do not introduce facts beyond what's \
in the supplied findings — your job is to connect and weigh what's already there, not add \
new claims. Respond with ONLY a JSON object with these keys:
- "overall_assessment": string, a synthesis of what the combined evidence shows
- "consensus_points": array of strings, specific findings that multiple sources agree on
  or that are well-supported by the gathered evidence
- "conflicting_findings": array of strings, contradictions or tensions between sources
- "evidence_strength": string, one of "strong", "moderate", "limited", "insufficient"
- "research_gaps": array of strings, areas where the gathered evidence is missing, sparse,
  or unclear
Do not include any text outside the JSON object."""

# Only the narrative/analytical fields matter for synthesis — full source
# lists (every trial's eligibility text, every paper title) would just
# dilute the prompt with data the synthesis doesn't need to reason about.
_RELEVANT_FIELDS = {
    "literature_review": ["summary", "key_findings", "evidence_level", "conclusions"],
    "drug_discovery": ["mechanism_of_action", "comparison_report", "candidate_drugs"],
    "clinical_trial_analyzer": ["trial_summary", "patient_population_analysis", "success_rates"],
    "safety": ["safety_summary", "key_risks", "notable_interactions", "signal_assessment"],
    "regulatory": ["regulatory_summary", "recall_summary", "notable_flags"],
}


def _condense(agent_results: dict[str, Any]) -> dict[str, Any]:
    condensed = {}
    for agent_name, fields in _RELEVANT_FIELDS.items():
        result = agent_results.get(agent_name)
        if not result:
            continue
        condensed[agent_name] = {f: result.get(f) for f in fields if result.get(f)}
    return condensed


class EvidenceSynthesisAgent(BaseAgent):
    """Runs after the specialist agents, as an orchestrator pipeline stage
    rather than a standalone endpoint — it needs their combined output as
    input, so it doesn't make sense to call on its own.
    """

    name = "evidence_synthesis"
    description = "Synthesizes findings across specialist agents into one cross-cutting evidence assessment."

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        agent_results = (context or {}).get("agent_results", {})
        condensed = _condense(agent_results)

        if not condensed:
            return {
                "agent": self.name,
                "query": query,
                "overall_assessment": None,
                "consensus_points": [],
                "conflicting_findings": [],
                "evidence_strength": None,
                "research_gaps": [],
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Research question: {query}\n\nFindings gathered by specialist agents:\n{json.dumps(condensed)}",
        )

        return {
            "agent": self.name,
            "query": query,
            "overall_assessment": analysis.get("overall_assessment"),
            "consensus_points": analysis.get("consensus_points", []),
            "conflicting_findings": analysis.get("conflicting_findings", []),
            "evidence_strength": analysis.get("evidence_strength"),
            "research_gaps": analysis.get("research_gaps", []),
        }
