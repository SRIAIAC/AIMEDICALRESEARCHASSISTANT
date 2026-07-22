import json
from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import ClinicalTrialsClient, get_clinicaltrials_client
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are a clinical trial analysis assistant. Given a condition and a \
list of trial records from ClinicalTrials.gov, produce an analysis grounded in the \
provided data. Respond with ONLY a JSON object with these keys:
- "trial_summary": string, an overview of the trial landscape for this condition
- "patient_population_analysis": string, a summary of typical eligibility criteria and enrollment sizes
Do not include any text outside the JSON object."""


class ClinicalTrialAnalyzerAgent(BaseAgent):
    name = "clinical_trial_analyzer"
    description = "Reads ClinicalTrials.gov data to compare phases, endpoints, populations, and outcomes."

    def __init__(
        self,
        clinicaltrials_client: ClinicalTrialsClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._trials = clinicaltrials_client or get_clinicaltrials_client()
        self._llm = llm_client or get_llm_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        studies = await self._trials.search(query, status=context.get("status"), phase=context.get("phase"))
        if not studies:
            return {
                "agent": self.name,
                "query": query,
                "trial_summary": None,
                "success_rates": {},
                "study_comparison": [],
                "patient_population_analysis": None,
                "timeline": [],
            }

        summarized = [ClinicalTrialsClient.summarize_study(study) for study in studies]

        success_rates: dict[str, int] = {}
        for study in summarized:
            status = study.get("status") or "UNKNOWN"
            success_rates[status] = success_rates.get(status, 0) + 1

        timeline = sorted(
            (
                {"nct_id": s["nct_id"], "start_date": s.get("start_date"), "completion_date": s.get("completion_date")}
                for s in summarized
                if s.get("start_date")
            ),
            key=lambda entry: entry["start_date"],
        )

        analysis = await self._llm.complete_json(
            system=SYSTEM_PROMPT,
            prompt=f"Condition: {query}\n\nTrials: {json.dumps(summarized)}",
        )

        return {
            "agent": self.name,
            "query": query,
            "trial_summary": analysis.get("trial_summary"),
            "success_rates": success_rates,
            "study_comparison": summarized,
            "patient_population_analysis": analysis.get("patient_population_analysis"),
            "timeline": timeline,
        }
