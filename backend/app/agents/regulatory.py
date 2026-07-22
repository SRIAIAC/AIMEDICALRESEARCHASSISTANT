import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import OpenFDAClient, get_openfda_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a regulatory intelligence assistant. Given FDA approval/submission \
history and recall records for a drug, produce a regulatory summary grounded strictly in that \
data. Respond with ONLY a JSON object with these keys:
- "regulatory_summary": string, an overview of the drug's current regulatory status
- "approval_timeline_summary": string, a summary of the approval/submission history (original
  approval, notable supplements)
- "recall_summary": string, a summary of any recalls, or a clear statement that none were found
- "notable_flags": array of strings, anything regulatory-notable worth a researcher's attention
  (e.g. recent recalls, an unusually high number of supplemental approvals, safety-related
  submissions)
Do not include any text outside the JSON object."""


class RegulatoryAgent(BaseAgent):
    name = "regulatory"
    description = "Tracks FDA approval history and recalls for a drug."

    def __init__(
        self,
        openfda_client: OpenFDAClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._openfda = openfda_client or get_openfda_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        approvals = await self._openfda.approval_history(query)
        recalls = await self._openfda.recalls(query)

        approval_summaries = [OpenFDAClient.summarize_approval(a) for a in approvals]
        recall_summaries = [OpenFDAClient.summarize_recall(r) for r in recalls]

        if not approval_summaries and not recall_summaries:
            return {
                "agent": self.name,
                "query": query,
                "regulatory_summary": None,
                "approval_timeline_summary": None,
                "recall_summary": None,
                "notable_flags": [],
                "approvals": [],
                "recalls": [],
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=(
                f"Drug: {query}\n\n"
                f"Approval records: {json.dumps(approval_summaries)}\n\n"
                f"Recall records: {json.dumps(recall_summaries)}"
            ),
        )

        return {
            "agent": self.name,
            "query": query,
            "regulatory_summary": analysis.get("regulatory_summary"),
            "approval_timeline_summary": analysis.get("approval_timeline_summary"),
            "recall_summary": analysis.get("recall_summary"),
            "notable_flags": analysis.get("notable_flags", []),
            "approvals": approval_summaries,
            "recalls": recall_summaries,
        }
