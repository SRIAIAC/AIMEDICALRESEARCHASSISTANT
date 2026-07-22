from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import OpenFDAClient, get_openfda_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a drug interaction research assistant. Given the FDA label \
interaction/warning text for two drugs, assess whether there is a plausible interaction \
between them based ONLY on what is stated in the provided label text. This is a text-based \
cross-reference of FDA labels, not a query against a dedicated drug-interaction database — \
be explicit about that limitation. If neither label mentions the other drug, its ingredient, \
or its drug class, say so rather than guessing at a mechanism. Respond with ONLY a JSON \
object with these keys:
- "interaction_found": boolean, whether the label text suggests a plausible interaction
- "risk_level": string, one of "high", "moderate", "low", "unclear" based on how the labels
  describe it ("unclear" if the labels don't address this combination)
- "explanation": string, what the label text does (or doesn't) say about this combination
- "recommendation": string, a cautious research-support note — never a clinical directive
  (e.g. "this combination warrants pharmacist or prescriber review")
Do not include any text outside the JSON object."""


class DrugInteractionAgent(BaseAgent):
    """Checks two drugs' FDA label text for a plausible interaction. Not a
    substitute for a dedicated drug-interaction database — RxNav's used to
    provide one but NLM discontinued that API, and there's no other free,
    no-key source for structured pairwise interaction data, so this reads
    both labels and has the LLM cross-reference them instead.
    """

    name = "drug_interaction"
    description = "Cross-references two drugs' FDA label text for a plausible interaction."

    def __init__(
        self,
        openfda_client: OpenFDAClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._openfda = openfda_client or get_openfda_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        drug_a = context.get("drug_a", query)
        drug_b = context.get("drug_b", "")

        labels_a = await self._openfda.drug_label(drug_a)
        labels_b = await self._openfda.drug_label(drug_b)
        safety_a = OpenFDAClient.extract_safety_fields(labels_a[0]) if labels_a else {}
        safety_b = OpenFDAClient.extract_safety_fields(labels_b[0]) if labels_b else {}

        if not safety_a.get("drug_interactions") and not safety_b.get("drug_interactions"):
            return {
                "agent": self.name,
                "query": query,
                "drug_a": drug_a,
                "drug_b": drug_b,
                "interaction_found": None,
                "risk_level": None,
                "explanation": None,
                "recommendation": None,
            }

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=(
                f"Drug A: {drug_a}\n"
                f"Label interaction/warning text for Drug A: {safety_a.get('drug_interactions') or 'Not specified'}\n\n"
                f"Drug B: {drug_b}\n"
                f"Label interaction/warning text for Drug B: {safety_b.get('drug_interactions') or 'Not specified'}"
            ),
        )

        return {
            "agent": self.name,
            "query": query,
            "drug_a": drug_a,
            "drug_b": drug_b,
            "interaction_found": analysis.get("interaction_found"),
            "risk_level": analysis.get("risk_level"),
            "explanation": analysis.get("explanation"),
            "recommendation": analysis.get("recommendation"),
        }
