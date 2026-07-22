import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import OpenFDAClient, get_openfda_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a drug safety and pharmacovigilance assistant. Given FDA label \
safety sections and a list of the most frequently reported adverse-event terms from FAERS \
(FDA Adverse Event Reporting System) for a drug, produce a safety profile grounded strictly \
in that data. Do not diagnose or give clinical advice — this is a research-support summary, \
not a clinical decision. Respond with ONLY a JSON object with these keys:
- "safety_summary": string, a concise overview of the drug's safety profile
- "key_risks": array of strings, the most important risks grounded in the label text
- "notable_interactions": array of strings, drug interactions worth flagging (from the label)
- "signal_assessment": string, a brief, careful interpretation of whether the FAERS adverse
  event pattern raises anything notable — explicitly note that FAERS counts are unverified,
  voluntary reports and do not by themselves establish causation
Do not include any text outside the JSON object."""


class SafetyAgent(BaseAgent):
    name = "safety"
    description = "Checks FDA label safety data and FAERS adverse-event reports for a drug."

    def __init__(
        self,
        openfda_client: OpenFDAClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._openfda = openfda_client or get_openfda_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        labels = await self._openfda.drug_label(query)
        safety_fields = OpenFDAClient.extract_safety_fields(labels[0]) if labels else {}
        adverse_events = await self._openfda.adverse_event_counts(query)

        if not any(safety_fields.values()) and not adverse_events:
            return {
                "agent": self.name,
                "query": query,
                "safety_summary": None,
                "key_risks": [],
                "notable_interactions": [],
                "signal_assessment": None,
                "contraindications": None,
                "drug_interactions": None,
                "top_adverse_events": [],
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=(
                f"Drug: {query}\n\n"
                f"FDA label safety sections: {json.dumps(safety_fields)}\n\n"
                f"Top FAERS adverse-event terms (voluntary reports, unverified): "
                f"{json.dumps(adverse_events)}"
            ),
        )

        return {
            "agent": self.name,
            "query": query,
            "safety_summary": analysis.get("safety_summary"),
            "key_risks": analysis.get("key_risks", []),
            "notable_interactions": analysis.get("notable_interactions", []),
            "signal_assessment": analysis.get("signal_assessment"),
            "contraindications": safety_fields.get("contraindications"),
            "drug_interactions": safety_fields.get("drug_interactions"),
            "top_adverse_events": adverse_events,
        }
