import asyncio
from typing import Any

from app.agents.base import BaseAgent
from app.agents.citation_generator import CitationGeneratorAgent
from app.agents.citation_verification import CitationVerificationAgent
from app.agents.clinical_trial_analyzer import ClinicalTrialAnalyzerAgent
from app.agents.drug_discovery import DrugDiscoveryAgent
from app.agents.evidence_synthesis import EvidenceSynthesisAgent
from app.agents.literature_review import LiteratureReviewAgent
from app.agents.regulatory import RegulatoryAgent
from app.agents.research_summarizer import ResearchSummarizerAgent
from app.agents.safety import SafetyAgent


class ResearchPlanner:
    """Fans a medical research query out to the specialized agents, then
    runs two more pipeline stages over their combined output: Evidence
    Synthesis (a cross-cutting assessment of what the gathered evidence
    shows) and Citation Verification (checks that synthesis claims are
    actually traceable to the sources the specialist agents retrieved,
    rather than trusting the LLM's synthesis at face value).

    Literature review runs first so its PubMed sources can seed the
    citation generator; the remaining specialist agents run concurrently.
    Any specialist agent that fails is recorded in `failed_agents` rather
    than taking down the whole report — a bad response from, say, the
    trials API shouldn't erase the literature review the user actually
    asked for.
    """

    def __init__(
        self,
        agents: list[BaseAgent] | None = None,
        evidence_synthesis_agent: EvidenceSynthesisAgent | None = None,
        citation_verification_agent: CitationVerificationAgent | None = None,
    ) -> None:
        self.agents: list[BaseAgent] = agents or [
            LiteratureReviewAgent(),
            DrugDiscoveryAgent(),
            ClinicalTrialAnalyzerAgent(),
            CitationGeneratorAgent(),
            ResearchSummarizerAgent(),
            SafetyAgent(),
            RegulatoryAgent(),
        ]
        self._evidence_synthesis_agent = evidence_synthesis_agent or EvidenceSynthesisAgent()
        self._citation_verification_agent = citation_verification_agent or CitationVerificationAgent()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = dict(context or {})
        failed_agents: dict[str, str] = {}

        literature_agent = next((a for a in self.agents if a.name == "literature_review"), None)
        literature_result: dict[str, Any] | None = None
        if literature_agent is not None:
            try:
                literature_result = await literature_agent.run(query, context)
            except Exception as exc:  # noqa: BLE001 - isolate so other agents still run
                failed_agents[literature_agent.name] = str(exc)

        pmids = [source["pmid"] for source in (literature_result or {}).get("sources", [])]
        citation_context = {**context, "pmids": pmids}

        other_agents = [a for a in self.agents if a.name != "literature_review"]
        gathered = await asyncio.gather(
            *(
                agent.run(query, citation_context if agent.name == "citation_generator" else context)
                for agent in other_agents
            ),
            return_exceptions=True,
        )

        agent_results: dict[str, Any] = {}
        if literature_result is not None:
            agent_results[literature_result["agent"]] = literature_result
        for agent, outcome in zip(other_agents, gathered):
            if isinstance(outcome, BaseException):
                failed_agents[agent.name] = str(outcome)
            else:
                agent_results[outcome["agent"]] = outcome

        evidence_synthesis = await self._run_evidence_synthesis(query, agent_results, failed_agents)
        citation_verification = await self._run_citation_verification(
            query, agent_results, evidence_synthesis, failed_agents
        )

        return {
            "query": query,
            "agents": agent_results,
            "evidence_synthesis": evidence_synthesis,
            "citation_verification": citation_verification,
            "failed_agents": failed_agents,
        }

    async def _run_evidence_synthesis(
        self, query: str, agent_results: dict[str, Any], failed_agents: dict[str, str]
    ) -> dict[str, Any] | None:
        try:
            return await self._evidence_synthesis_agent.run(query, {"agent_results": agent_results})
        except Exception as exc:  # noqa: BLE001 - a failed synthesis shouldn't erase specialist results
            failed_agents["evidence_synthesis"] = str(exc)
            return None

    async def _run_citation_verification(
        self,
        query: str,
        agent_results: dict[str, Any],
        evidence_synthesis: dict[str, Any] | None,
        failed_agents: dict[str, str],
    ) -> dict[str, Any] | None:
        if not evidence_synthesis:
            return None

        claims = [
            *evidence_synthesis.get("consensus_points", []),
            *evidence_synthesis.get("conflicting_findings", []),
        ]

        sources: list[dict[str, Any]] = []
        literature = agent_results.get("literature_review", {})
        for source in literature.get("sources", []):
            sources.append({"id": source.get("pmid"), "label": source.get("title")})

        trials = agent_results.get("clinical_trial_analyzer", {})
        for study in trials.get("study_comparison", []):
            sources.append({"id": study.get("nct_id"), "label": study.get("title")})

        try:
            return await self._citation_verification_agent.run(query, {"claims": claims, "sources": sources})
        except Exception as exc:  # noqa: BLE001 - same isolation rationale as above
            failed_agents["citation_verification"] = str(exc)
            return None
