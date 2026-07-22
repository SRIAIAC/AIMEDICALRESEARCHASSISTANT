import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import OpenFDAClient, get_openfda_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a comparative drug analysis assistant. Given FDA label data for \
several drugs, produce a structured side-by-side comparison grounded strictly in the \
provided data — do not introduce outside knowledge about drugs whose data wasn't provided. \
Respond with ONLY a JSON object with these keys:
- "comparison_summary": string, an overview of how these drugs compare
- "comparison_table": array of objects, one per drug, each with "drug" (string),
  "mechanism_of_action" (string or null), "indications" (string or null), "key_risks"
  (array of strings)
- "efficacy_comparison": string, what the provided data does (or doesn't) support about
  relative efficacy
- "safety_comparison": string, a comparison of the safety profiles
Do not include any text outside the JSON object."""


class ComparativeAnalysisAgent(BaseAgent):
    name = "comparative_analysis"
    description = "Compares multiple drugs side-by-side across mechanism, indications, and safety."

    def __init__(
        self,
        openfda_client: OpenFDAClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._openfda = openfda_client or get_openfda_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        drug_names: list[str] = (context or {}).get("drug_names", [])
        drug_data: dict[str, Any] = {}
        for name in drug_names:
            labels = await self._openfda.drug_label(name)
            if labels:
                drug_data[name] = {
                    **OpenFDAClient.extract_label_fields(labels[0]),
                    **OpenFDAClient.extract_safety_fields(labels[0]),
                }

        if not drug_data:
            return self._empty_result(query, drug_names)

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Drugs to compare: {drug_names}\n\nData gathered: {json.dumps(drug_data)}",
        )

        return {
            "agent": self.name,
            "query": query,
            "drug_names": drug_names,
            "comparison_summary": analysis.get("comparison_summary"),
            "comparison_table": analysis.get("comparison_table", []),
            "efficacy_comparison": analysis.get("efficacy_comparison"),
            "safety_comparison": analysis.get("safety_comparison"),
        }

    def _empty_result(self, query: str, drug_names: list[str]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "query": query,
            "drug_names": drug_names,
            "comparison_summary": None,
            "comparison_table": [],
            "efficacy_comparison": None,
            "safety_comparison": None,
        }
