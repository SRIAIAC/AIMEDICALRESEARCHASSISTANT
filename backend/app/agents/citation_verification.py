import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a citation verification assistant. Given a list of claims from a \
medical research synthesis and a list of the actual source documents (papers, trials) that \
were retrieved to support that research, check whether each claim is traceable to at least \
one listed source. Be conservative: a generic or vague claim that isn't clearly backed by a \
specific listed source should be marked unsupported rather than assumed fine — this check \
exists specifically to catch unsupported AI-generated claims before they reach the user. \
Respond with ONLY a JSON object with these keys:
- "verified_claims": array of objects, each with "claim" (string) and "supporting_source"
  (string — the id or title of the specific listed source that backs it)
- "unsupported_claims": array of strings, claims from the input that could not be traced to
  any listed source
- "verification_summary": string, one or two sentences on how well-grounded the synthesis
  is overall
Do not include any text outside the JSON object."""


class CitationVerificationAgent(BaseAgent):
    """The last orchestrator pipeline stage — checks the Evidence Synthesis
    agent's claims against the actual sources the other agents retrieved,
    so unsupported claims are flagged rather than silently presented as
    fact. Like Evidence Synthesis, this only makes sense as part of the
    orchestrator pipeline, not as a standalone endpoint.
    """

    name = "citation_verification"
    description = "Checks whether synthesis claims are grounded in the actual retrieved sources."

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        claims: list[str] = context.get("claims", [])
        sources: list[dict[str, Any]] = context.get("sources", [])

        if not claims or not sources:
            return {
                "agent": self.name,
                "query": query,
                "verified_claims": [],
                "unsupported_claims": list(claims),
                "verification_summary": "No sources were available to verify claims against."
                if claims
                else None,
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Claims to verify:\n{json.dumps(claims)}\n\nAvailable sources:\n{json.dumps(sources)}",
        )

        return {
            "agent": self.name,
            "query": query,
            "verified_claims": analysis.get("verified_claims", []),
            "unsupported_claims": analysis.get("unsupported_claims", []),
            "verification_summary": analysis.get("verification_summary"),
        }
