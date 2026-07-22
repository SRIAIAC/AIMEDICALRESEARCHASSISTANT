import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import OpenFDAClient, RxNormClient, get_openfda_client, get_rxnorm_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a drug discovery research assistant. Given FDA label data \
and a list of pharmacologically related compounds for a drug, synthesize a candidate \
analysis. Ground mechanism-of-action claims in the FDA label data when it is provided. \
Respond with ONLY a JSON object with these keys:
- "candidate_drugs": array of strings, drugs worth investigating (repurposing candidates or close analogs)
- "mechanism_of_action": string
- "similar_compounds": array of strings
- "comparison_report": string, a short comparison of the candidates against the queried drug
Do not include any text outside the JSON object."""


class DrugDiscoveryAgent(BaseAgent):
    name = "drug_discovery"
    description = "Searches drug databases to suggest candidates, compare compounds, and analyze mechanisms."

    def __init__(
        self,
        openfda_client: OpenFDAClient | None = None,
        rxnorm_client: RxNormClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._openfda = openfda_client or get_openfda_client()
        self._rxnorm = rxnorm_client or get_rxnorm_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        labels = await self._openfda.drug_label(query)
        label_fields = OpenFDAClient.extract_label_fields(labels[0]) if labels else {}

        rxcui = await self._rxnorm.find_rxcui(query)
        related = await self._rxnorm.related_drug_names(rxcui) if rxcui else []

        if not label_fields.get("mechanism_of_action") and not related:
            return {
                "agent": self.name,
                "query": query,
                "candidate_drugs": [],
                "mechanism_of_action": None,
                "similar_compounds": [],
                "comparison_report": None,
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=(
                f"Drug: {query}\n\n"
                f"FDA label data: {json.dumps(label_fields)}\n\n"
                f"Pharmacologically related compounds (RxNorm): {related}"
            ),
        )

        return {
            "agent": self.name,
            "query": query,
            "candidate_drugs": analysis.get("candidate_drugs", []),
            "mechanism_of_action": analysis.get("mechanism_of_action") or label_fields.get("mechanism_of_action"),
            "similar_compounds": analysis.get("similar_compounds") or related,
            "comparison_report": analysis.get("comparison_report"),
        }
