import json
from typing import Any

import pytest

from app.agents.citation_generator import CitationGeneratorAgent
from app.agents.citation_verification import CitationVerificationAgent
from app.agents.clinical_trial_analyzer import ClinicalTrialAnalyzerAgent
from app.agents.comparative_analysis import ComparativeAnalysisAgent
from app.agents.document_qa import DocumentQAAgent
from app.agents.drug_discovery import DrugDiscoveryAgent
from app.agents.drug_interaction import DrugInteractionAgent
from app.agents.evidence_synthesis import EvidenceSynthesisAgent
from app.agents.literature_review import LiteratureReviewAgent
from app.agents.orchestrator import ResearchPlanner
from app.agents.points_summarizer import PointsSummarizerAgent
from app.agents.regulatory import RegulatoryAgent
from app.agents.research_paper_analyzer import ResearchPaperAnalyzerAgent
from app.agents.research_summarizer import ResearchSummarizerAgent
from app.agents.safety import SafetyAgent
from app.agents.web_search_rag import WebSearchRAGAgent
from app.services.llm import LLMClient


class FakeLLMClient(LLMClient):
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, prompt: str, max_tokens: int = 1024, json_mode: bool = False) -> str:
        self.calls.append((system, prompt))
        return json.dumps(self._response)


class FakePubMedClient:
    def __init__(self, pmids: list[str] | None = None) -> None:
        self._pmids = pmids if pmids is not None else ["111", "222"]

    async def search(self, term: str, max_results: int = 20) -> list[str]:
        return self._pmids

    async def fetch_summaries(self, pmids: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "uid": pmid,
                "title": f"Study {pmid}",
                "fulljournalname": "Journal of Testing",
                "pubdate": "2021 Jan",
                "authors": [{"name": "Smith JA"}],
                "articleids": [{"idtype": "doi", "value": f"10.1/{pmid}"}],
            }
            for pmid in pmids
        ]

    async def fetch_abstracts(self, pmids: list[str]) -> dict[str, str]:
        return {pmid: f"Abstract text for {pmid}" for pmid in pmids}


class FakeVectorStore:
    def __init__(self, query_results: list[dict[str, Any]] | None = None) -> None:
        self.upserted: list[dict[str, Any]] = []
        self._query_results = query_results if query_results is not None else []

    def upsert(self, ids, embeddings, metadatas) -> None:
        self.upserted.append({"ids": ids, "embeddings": embeddings, "metadatas": metadatas})

    def query(self, embedding, top_k=5):
        return self._query_results


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] for t in texts]


class FakeOpenFDAClient:
    def __init__(
        self,
        labels: list[dict[str, Any]] | None = None,
        adverse_events: list[dict[str, Any]] | None = None,
        approvals: list[dict[str, Any]] | None = None,
        recalls: list[dict[str, Any]] | None = None,
        labels_by_name: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self._labels_by_name = labels_by_name
        self._labels = labels if labels is not None else [
            {
                "openfda": {"brand_name": ["Glucophage"], "generic_name": ["metformin"]},
                "mechanism_of_action": ["Decreases hepatic glucose production."],
                "indications_and_usage": ["Type 2 diabetes."],
                "contraindications": ["Severe renal impairment."],
                "drug_interactions": ["Concomitant use with alcohol increases risk of lactic acidosis."],
            }
        ]
        self._adverse_events = adverse_events if adverse_events is not None else [
            {"term": "NAUSEA", "count": 120},
            {"term": "DIARRHOEA", "count": 95},
        ]
        self._approvals = approvals if approvals is not None else [
            {
                "sponsor_name": "Test Sponsor",
                "application_number": "NDA123456",
                "products": [{"brand_name": "Glucophage", "dosage_form": "TABLET", "route": "ORAL", "marketing_status": "Prescription"}],
                "submissions": [
                    {"submission_status_date": "19950101", "submission_class_code_description": "New Molecular Entity"},
                    {"submission_status_date": "20100615", "submission_class_code_description": "Labeling"},
                ],
            }
        ]
        self._recalls = recalls if recalls is not None else [
            {
                "recall_number": "D-1234-2020",
                "status": "Terminated",
                "classification": "Class II",
                "reason_for_recall": "Mislabeling",
                "product_description": "Glucophage Tablet",
                "recall_initiation_date": "20200101",
                "voluntary_mandated": "Voluntary: Firm initiated",
            }
        ]

    async def drug_label(self, drug_name: str) -> list[dict[str, Any]]:
        if self._labels_by_name is not None:
            return self._labels_by_name.get(drug_name, [])
        return self._labels

    async def adverse_event_counts(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._adverse_events[:limit]

    async def approval_history(self, drug_name: str) -> list[dict[str, Any]]:
        return self._approvals

    async def recalls(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._recalls[:limit]


class FakeRxNormClient:
    def __init__(self, rxcui: str | None = "6809", related: list[str] | None = None) -> None:
        self._rxcui = rxcui
        self._related = related if related is not None else ["glipizide", "sitagliptin"]

    async def find_rxcui(self, drug_name: str) -> str | None:
        return self._rxcui

    async def related_drug_names(self, rxcui: str) -> list[str]:
        return self._related


class FakeClinicalTrialsClient:
    def __init__(self, studies: list[dict[str, Any]] | None = None) -> None:
        self._studies = studies if studies is not None else [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT001", "briefTitle": "Trial One"},
                    "statusModule": {
                        "overallStatus": "COMPLETED",
                        "startDateStruct": {"date": "2019-01"},
                        "completionDateStruct": {"date": "2020-06"},
                    },
                    "designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 200}},
                    "eligibilityModule": {
                        "eligibilityCriteria": "Adults with type 2 diabetes",
                        "minimumAge": "18 Years",
                        "maximumAge": "75 Years",
                    },
                }
            },
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT002", "briefTitle": "Trial Two"},
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "designModule": {"phases": ["PHASE2"], "enrollmentInfo": {"count": 80}},
                    "eligibilityModule": {"eligibilityCriteria": "Adults", "minimumAge": "18 Years"},
                }
            },
        ]

    async def search(
        self, condition: str, status: str | None = None, phase: str | None = None, page_size: int = 20
    ) -> list[dict[str, Any]]:
        return self._studies


class FailingAgent:
    """Test double for an agent whose run() raises — used to verify the
    orchestrator isolates one bad agent instead of failing the whole report.
    """

    name = "failing_agent"

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        raise RuntimeError("simulated agent failure")


class FakeWebSearchClient:
    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results if results is not None else [
            {
                "title": "Aspirin",
                "url": "https://en.wikipedia.org/wiki/Aspirin",
                "snippet": "Aspirin inhibits platelet aggregation via irreversible COX-1 inhibition.",
                "source": "wikipedia",
            }
        ]

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._results[:limit]


class FakeEvidenceSynthesisAgent:
    name = "evidence_synthesis"

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "agent": self.name,
            "query": query,
            "overall_assessment": "synthesized",
            "consensus_points": ["Metformin lowers HbA1c"],
            "conflicting_findings": [],
            "evidence_strength": "moderate",
            "research_gaps": [],
        }


class FakeCitationVerificationAgent:
    name = "citation_verification"

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "agent": self.name,
            "query": query,
            "verified_claims": [{"claim": "Metformin lowers HbA1c", "supporting_source": "111"}],
            "unsupported_claims": [],
            "verification_summary": "Well grounded.",
        }


@pytest.mark.asyncio
async def test_literature_review_agent_builds_report_from_pubmed_and_llm() -> None:
    llm = FakeLLMClient(
        {
            "summary": "Metformin is effective for type 2 diabetes.",
            "key_findings": ["Reduces HbA1c"],
            "evidence_level": "Moderate",
            "conclusions": ["More long-term data needed"],
        }
    )
    vector_store = FakeVectorStore()
    agent = LiteratureReviewAgent(
        pubmed_client=FakePubMedClient(),
        vector_store=vector_store,
        embedder=FakeEmbedder(),
        llm_client=llm,
    )

    result = await agent.run("type 2 diabetes")

    assert result["agent"] == "literature_review"
    assert result["summary"] == "Metformin is effective for type 2 diabetes."
    assert result["evidence_level"] == "Moderate"
    assert {s["pmid"] for s in result["sources"]} == {"111", "222"}
    assert len(vector_store.upserted) == 1


@pytest.mark.asyncio
async def test_literature_review_agent_handles_no_results() -> None:
    agent = LiteratureReviewAgent(
        pubmed_client=FakePubMedClient(pmids=[]),
        vector_store=FakeVectorStore(),
        embedder=FakeEmbedder(),
        llm_client=FakeLLMClient({}),
    )

    result = await agent.run("an extremely obscure topic")

    assert result["summary"] is None
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_drug_discovery_agent_uses_label_and_related_compounds() -> None:
    llm = FakeLLMClient(
        {
            "candidate_drugs": ["sitagliptin"],
            "mechanism_of_action": "Activates AMPK, decreasing hepatic glucose output.",
            "similar_compounds": ["glipizide"],
            "comparison_report": "Both lower blood glucose via different pathways.",
        }
    )
    agent = DrugDiscoveryAgent(
        openfda_client=FakeOpenFDAClient(),
        rxnorm_client=FakeRxNormClient(),
        llm_client=llm,
    )

    result = await agent.run("metformin")

    assert result["candidate_drugs"] == ["sitagliptin"]
    assert "AMPK" in result["mechanism_of_action"]
    assert result["similar_compounds"] == ["glipizide"]


@pytest.mark.asyncio
async def test_drug_discovery_agent_handles_no_data() -> None:
    agent = DrugDiscoveryAgent(
        openfda_client=FakeOpenFDAClient(labels=[]),
        rxnorm_client=FakeRxNormClient(rxcui=None, related=[]),
        llm_client=FakeLLMClient({}),
    )

    result = await agent.run("an unknown compound")

    assert result["candidate_drugs"] == []
    assert result["mechanism_of_action"] is None


@pytest.mark.asyncio
async def test_clinical_trial_analyzer_agent_aggregates_success_rates() -> None:
    llm = FakeLLMClient(
        {
            "trial_summary": "Two trials found for this condition.",
            "patient_population_analysis": "Mostly adults 18-75.",
        }
    )
    agent = ClinicalTrialAnalyzerAgent(clinicaltrials_client=FakeClinicalTrialsClient(), llm_client=llm)

    result = await agent.run("type 2 diabetes")

    assert result["success_rates"] == {"COMPLETED": 1, "RECRUITING": 1}
    assert len(result["study_comparison"]) == 2
    assert result["timeline"] == [{"nct_id": "NCT001", "start_date": "2019-01", "completion_date": "2020-06"}]


@pytest.mark.asyncio
async def test_clinical_trial_analyzer_agent_handles_no_studies() -> None:
    agent = ClinicalTrialAnalyzerAgent(
        clinicaltrials_client=FakeClinicalTrialsClient(studies=[]), llm_client=FakeLLMClient({})
    )

    result = await agent.run("an extremely rare condition")

    assert result["trial_summary"] is None
    assert result["study_comparison"] == []


@pytest.mark.asyncio
async def test_citation_generator_agent_with_explicit_references() -> None:
    agent = CitationGeneratorAgent(pubmed_client=FakePubMedClient())
    references = [
        {"authors": ["Smith JA"], "title": "A study", "journal": "Journal X", "year": "2020", "doi": "10.1/x"}
    ]

    result = await agent.run("ignored", context={"references": references, "format": "Vancouver"})

    assert result["format"] == "Vancouver"
    assert result["inline_citations"] == ["[1]"]
    assert result["doi_links"] == ["https://doi.org/10.1/x"]


@pytest.mark.asyncio
async def test_citation_generator_agent_fetches_by_pmid() -> None:
    agent = CitationGeneratorAgent(pubmed_client=FakePubMedClient())

    result = await agent.run("111,222", context={"format": "APA"})

    assert len(result["bibliography"]) == 2


@pytest.mark.asyncio
async def test_research_summarizer_agent_with_text() -> None:
    llm = FakeLLMClient(
        {
            "one_page_summary": "Summary.",
            "executive_summary": "Short summary.",
            "key_findings": ["finding one"],
            "clinical_implications": ["implication one"],
        }
    )
    agent = ResearchSummarizerAgent(llm_client=llm)

    result = await agent.run("metformin", context={"text": "Some long research paper text."})

    assert result["executive_summary"] == "Short summary."
    assert result["key_findings"] == ["finding one"]


@pytest.mark.asyncio
async def test_research_summarizer_agent_handles_no_text() -> None:
    agent = ResearchSummarizerAgent(llm_client=FakeLLMClient({}))

    result = await agent.run("metformin")

    assert result["one_page_summary"] is None


@pytest.mark.asyncio
async def test_safety_agent_uses_label_and_faers_data() -> None:
    llm = FakeLLMClient(
        {
            "safety_summary": "Generally well tolerated; GI effects common.",
            "key_risks": ["Lactic acidosis in renal impairment"],
            "notable_interactions": ["Alcohol increases lactic acidosis risk"],
            "signal_assessment": "FAERS pattern consistent with known GI tolerability profile.",
        }
    )
    agent = SafetyAgent(openfda_client=FakeOpenFDAClient(), llm_client=llm)

    result = await agent.run("metformin")

    assert result["agent"] == "safety"
    assert result["contraindications"] == "Severe renal impairment."
    assert result["top_adverse_events"] == [{"term": "NAUSEA", "count": 120}, {"term": "DIARRHOEA", "count": 95}]
    assert result["key_risks"] == ["Lactic acidosis in renal impairment"]


@pytest.mark.asyncio
async def test_safety_agent_handles_no_data() -> None:
    agent = SafetyAgent(
        openfda_client=FakeOpenFDAClient(labels=[], adverse_events=[]), llm_client=FakeLLMClient({})
    )

    result = await agent.run("an unknown compound")

    assert result["safety_summary"] is None
    assert result["top_adverse_events"] == []


@pytest.mark.asyncio
async def test_regulatory_agent_summarizes_approvals_and_recalls() -> None:
    llm = FakeLLMClient(
        {
            "regulatory_summary": "Approved and currently marketed; one historical recall.",
            "approval_timeline_summary": "Originally approved 1995, labeling update 2010.",
            "recall_summary": "One Class II recall in 2020 for mislabeling.",
            "notable_flags": ["Historical mislabeling recall"],
        }
    )
    agent = RegulatoryAgent(openfda_client=FakeOpenFDAClient(), llm_client=llm)

    result = await agent.run("metformin")

    assert result["agent"] == "regulatory"
    assert len(result["approvals"]) == 1
    assert result["approvals"][0]["sponsor"] == "Test Sponsor"
    assert result["approvals"][0]["first_approval_date"] == "19950101"
    assert result["recalls"][0]["recall_number"] == "D-1234-2020"
    assert result["notable_flags"] == ["Historical mislabeling recall"]


@pytest.mark.asyncio
async def test_regulatory_agent_handles_no_data() -> None:
    agent = RegulatoryAgent(
        openfda_client=FakeOpenFDAClient(approvals=[], recalls=[]), llm_client=FakeLLMClient({})
    )

    result = await agent.run("an unknown compound")

    assert result["regulatory_summary"] is None
    assert result["approvals"] == []


@pytest.mark.asyncio
async def test_research_paper_analyzer_extracts_from_pmid() -> None:
    llm = FakeLLMClient(
        {
            "objectives": "Assess metformin efficacy.",
            "methodology": "Randomized controlled trial.",
            "patient_population": "200 adults with type 2 diabetes.",
            "interventions": ["Metformin 500mg BID"],
            "endpoints": ["HbA1c change at 12 weeks"],
            "results": "HbA1c reduced by 1.2%.",
            "statistical_findings": ["p < 0.001"],
            "limitations": ["Single-center study"],
            "conclusions": "Metformin significantly reduced HbA1c.",
        }
    )
    agent = ResearchPaperAnalyzerAgent(pubmed_client=FakePubMedClient(), llm_client=llm)

    result = await agent.run("111", context={"pmid": "111"})

    assert result["agent"] == "research_paper_analyzer"
    assert result["title"] == "Study 111"
    assert result["methodology"] == "Randomized controlled trial."
    assert result["statistical_findings"] == ["p < 0.001"]


@pytest.mark.asyncio
async def test_research_paper_analyzer_extracts_from_raw_text() -> None:
    llm = FakeLLMClient({"objectives": "Test objective from raw text."})
    agent = ResearchPaperAnalyzerAgent(pubmed_client=FakePubMedClient(), llm_client=llm)

    result = await agent.run("A Paper Title", context={"text": "Some full paper text."})

    assert result["title"] == "A Paper Title"
    assert result["objectives"] == "Test objective from raw text."


@pytest.mark.asyncio
async def test_research_paper_analyzer_handles_no_input() -> None:
    agent = ResearchPaperAnalyzerAgent(pubmed_client=FakePubMedClient(), llm_client=FakeLLMClient({}))

    result = await agent.run("nothing supplied", context={})

    assert result["objectives"] is None
    assert result["interventions"] == []


@pytest.mark.asyncio
async def test_drug_interaction_agent_cross_references_labels() -> None:
    llm = FakeLLMClient(
        {
            "interaction_found": True,
            "risk_level": "moderate",
            "explanation": "Drug A's label mentions increased risk with Drug B's class.",
            "recommendation": "Consult a pharmacist before combining.",
        }
    )
    openfda_client = FakeOpenFDAClient(
        labels_by_name={
            "warfarin": [{"drug_interactions": ["Increases risk when combined with anticoagulants."]}],
            "aspirin": [{"drug_interactions": ["May increase bleeding risk."]}],
        }
    )
    agent = DrugInteractionAgent(openfda_client=openfda_client, llm_client=llm)

    result = await agent.run("warfarin", context={"drug_a": "warfarin", "drug_b": "aspirin"})

    assert result["interaction_found"] is True
    assert result["risk_level"] == "moderate"
    assert result["drug_a"] == "warfarin"
    assert result["drug_b"] == "aspirin"


@pytest.mark.asyncio
async def test_drug_interaction_agent_handles_no_interaction_data() -> None:
    agent = DrugInteractionAgent(
        openfda_client=FakeOpenFDAClient(labels=[]), llm_client=FakeLLMClient({})
    )

    result = await agent.run("obscure drug a", context={"drug_a": "obscure drug a", "drug_b": "obscure drug b"})

    assert result["interaction_found"] is None


@pytest.mark.asyncio
async def test_comparative_analysis_agent_compares_drugs() -> None:
    llm = FakeLLMClient(
        {
            "comparison_summary": "Both are oral antidiabetics with different mechanisms.",
            "comparison_table": [
                {"drug": "metformin", "mechanism_of_action": "Decreases hepatic glucose production.", "indications": "Type 2 diabetes.", "key_risks": []}
            ],
            "efficacy_comparison": "Data doesn't directly compare efficacy.",
            "safety_comparison": "Both generally well tolerated.",
        }
    )
    agent = ComparativeAnalysisAgent(openfda_client=FakeOpenFDAClient(), llm_client=llm)

    result = await agent.run("metformin vs glipizide", context={"drug_names": ["metformin", "glipizide"]})

    assert result["agent"] == "comparative_analysis"
    assert len(result["comparison_table"]) == 1
    assert result["comparison_summary"] is not None


@pytest.mark.asyncio
async def test_comparative_analysis_agent_handles_no_data() -> None:
    agent = ComparativeAnalysisAgent(
        openfda_client=FakeOpenFDAClient(labels=[]), llm_client=FakeLLMClient({})
    )

    result = await agent.run("a vs b", context={"drug_names": ["unknown a", "unknown b"]})

    assert result["comparison_summary"] is None
    assert result["comparison_table"] == []


@pytest.mark.asyncio
async def test_web_search_rag_agent_answers_from_search_results() -> None:
    llm = FakeLLMClient(
        {
            "answer": "Aspirin blocks platelet aggregation via irreversible COX-1 inhibition.",
            "key_points": ["Inhibits COX-1 irreversibly", "Reduces platelet aggregation"],
            "supporting_sources": ["Aspirin"],
            "confidence": "high",
        }
    )
    agent = WebSearchRAGAgent(web_search_client=FakeWebSearchClient(), llm_client=llm)

    result = await agent.run("How does aspirin affect platelets?")

    assert result["agent"] == "web_search_rag"
    assert result["confidence"] == "high"
    assert result["key_points"] == ["Inhibits COX-1 irreversibly", "Reduces platelet aggregation"]
    assert result["sources"][0]["title"] == "Aspirin"


@pytest.mark.asyncio
async def test_web_search_rag_agent_handles_no_results() -> None:
    agent = WebSearchRAGAgent(web_search_client=FakeWebSearchClient(results=[]), llm_client=FakeLLMClient({}))

    result = await agent.run("a query with nothing found")

    assert result["answer"] is None
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_points_summarizer_agent_returns_bullet_points() -> None:
    llm = FakeLLMClient(
        {
            "title": "Metformin overview",
            "points": ["Reduces hepatic glucose production", "First-line for type 2 diabetes"],
            "key_takeaway": "Metformin is first-line therapy for type 2 diabetes.",
        }
    )
    agent = PointsSummarizerAgent(llm_client=llm)

    result = await agent.run("metformin", context={"text": "Metformin is a biguanide used for type 2 diabetes."})

    assert result["agent"] == "points_summarizer"
    assert len(result["points"]) == 2
    assert result["key_takeaway"] == "Metformin is first-line therapy for type 2 diabetes."


@pytest.mark.asyncio
async def test_points_summarizer_agent_handles_no_text() -> None:
    agent = PointsSummarizerAgent(llm_client=FakeLLMClient({}))

    result = await agent.run("metformin", context={"text": ""})

    assert result["points"] == []


@pytest.mark.asyncio
async def test_document_qa_agent_answers_from_retrieved_chunks() -> None:
    llm = FakeLLMClient(
        {
            "answer": "Metformin's primary mechanism is decreased hepatic glucose production.",
            "supporting_sources": ["111"],
            "confidence": "high",
        }
    )
    vector_store = FakeVectorStore(
        query_results=[
            {"source": "pubmed", "pmid": "111", "title": "Study 111", "text": "Metformin decreases hepatic glucose output."}
        ]
    )
    agent = DocumentQAAgent(embedder=FakeEmbedder(), vector_store=vector_store, llm_client=llm)

    result = await agent.run("How does metformin work?")

    assert result["agent"] == "document_qa"
    assert result["confidence"] == "high"
    assert result["sources"][0]["id"] == "111"


@pytest.mark.asyncio
async def test_document_qa_agent_handles_no_matches() -> None:
    agent = DocumentQAAgent(embedder=FakeEmbedder(), vector_store=FakeVectorStore(), llm_client=FakeLLMClient({}))

    result = await agent.run("a question with nothing indexed")

    assert result["answer"] is None
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_evidence_synthesis_agent_condenses_specialist_outputs() -> None:
    llm = FakeLLMClient(
        {
            "overall_assessment": "Evidence supports metformin as first-line therapy.",
            "consensus_points": ["Reduces HbA1c"],
            "conflicting_findings": [],
            "evidence_strength": "strong",
            "research_gaps": ["Limited pediatric data"],
        }
    )
    agent = EvidenceSynthesisAgent(llm_client=llm)
    agent_results = {
        "literature_review": {"summary": "s", "key_findings": ["Reduces HbA1c"], "evidence_level": "High"},
        "safety": {"safety_summary": "Well tolerated", "key_risks": []},
    }

    result = await agent.run("metformin", context={"agent_results": agent_results})

    assert result["evidence_strength"] == "strong"
    assert result["research_gaps"] == ["Limited pediatric data"]


@pytest.mark.asyncio
async def test_evidence_synthesis_agent_handles_no_agent_results() -> None:
    agent = EvidenceSynthesisAgent(llm_client=FakeLLMClient({}))

    result = await agent.run("metformin", context={"agent_results": {}})

    assert result["overall_assessment"] is None


@pytest.mark.asyncio
async def test_citation_verification_agent_flags_unsupported_claims() -> None:
    llm = FakeLLMClient(
        {
            "verified_claims": [{"claim": "Reduces HbA1c", "supporting_source": "111"}],
            "unsupported_claims": ["Cures diabetes entirely"],
            "verification_summary": "Mostly well grounded, one overreaching claim.",
        }
    )
    agent = CitationVerificationAgent(llm_client=llm)

    result = await agent.run(
        "metformin",
        context={
            "claims": ["Reduces HbA1c", "Cures diabetes entirely"],
            "sources": [{"id": "111", "label": "Study 111"}],
        },
    )

    assert result["unsupported_claims"] == ["Cures diabetes entirely"]


@pytest.mark.asyncio
async def test_citation_verification_agent_handles_no_sources() -> None:
    agent = CitationVerificationAgent(llm_client=FakeLLMClient({}))

    result = await agent.run("metformin", context={"claims": ["Some claim"], "sources": []})

    assert result["unsupported_claims"] == ["Some claim"]


@pytest.mark.asyncio
async def test_research_planner_fans_out_and_seeds_citations_from_literature() -> None:
    literature_llm = FakeLLMClient(
        {"summary": "s", "key_findings": [], "evidence_level": "Low", "conclusions": []}
    )
    planner = ResearchPlanner(
        agents=[
            LiteratureReviewAgent(
                pubmed_client=FakePubMedClient(),
                vector_store=FakeVectorStore(),
                embedder=FakeEmbedder(),
                llm_client=literature_llm,
            ),
            DrugDiscoveryAgent(
                openfda_client=FakeOpenFDAClient(),
                rxnorm_client=FakeRxNormClient(),
                llm_client=FakeLLMClient(
                    {"candidate_drugs": [], "mechanism_of_action": "x", "similar_compounds": [], "comparison_report": "x"}
                ),
            ),
            ClinicalTrialAnalyzerAgent(
                clinicaltrials_client=FakeClinicalTrialsClient(),
                llm_client=FakeLLMClient({"trial_summary": "x", "patient_population_analysis": "x"}),
            ),
            CitationGeneratorAgent(pubmed_client=FakePubMedClient()),
            ResearchSummarizerAgent(llm_client=FakeLLMClient({})),
        ],
        evidence_synthesis_agent=FakeEvidenceSynthesisAgent(),
        citation_verification_agent=FakeCitationVerificationAgent(),
    )

    report = await planner.run("metformin")

    assert set(report["agents"]) == {
        "literature_review",
        "drug_discovery",
        "clinical_trial_analyzer",
        "citation_generator",
        "research_summarizer",
    }
    assert len(report["agents"]["citation_generator"]["bibliography"]) == 2
    assert report["failed_agents"] == {}
    assert report["evidence_synthesis"]["evidence_strength"] == "moderate"
    assert report["citation_verification"]["verification_summary"] == "Well grounded."


@pytest.mark.asyncio
async def test_research_planner_isolates_a_failing_agent() -> None:
    literature_llm = FakeLLMClient(
        {"summary": "s", "key_findings": [], "evidence_level": "Low", "conclusions": []}
    )
    planner = ResearchPlanner(
        agents=[
            LiteratureReviewAgent(
                pubmed_client=FakePubMedClient(),
                vector_store=FakeVectorStore(),
                embedder=FakeEmbedder(),
                llm_client=literature_llm,
            ),
            ResearchSummarizerAgent(llm_client=FakeLLMClient({})),
            FailingAgent(),
        ],
        evidence_synthesis_agent=FakeEvidenceSynthesisAgent(),
        citation_verification_agent=FakeCitationVerificationAgent(),
    )

    report = await planner.run("metformin")

    assert set(report["agents"]) == {"literature_review", "research_summarizer"}
    assert report["failed_agents"] == {"failing_agent": "simulated agent failure"}
    # A failed specialist agent shouldn't stop the later pipeline stages from running.
    assert report["evidence_synthesis"] is not None
    assert report["citation_verification"] is not None
