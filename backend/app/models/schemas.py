from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Disease, drug, or research topic")
    context: dict[str, Any] | None = None


class ResearchReportResponse(BaseModel):
    id: str | None = None
    query: str
    agents: dict[str, Any]
    evidence_synthesis: dict[str, Any] | None = None
    citation_verification: dict[str, Any] | None = None
    failed_agents: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResearchReportSummary(BaseModel):
    id: str
    query: str
    created_at: datetime
    failed_agents: dict[str, str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class LiteratureSearchRequest(BaseModel):
    topic: str
    max_results: int = 20


class DrugLookupRequest(BaseModel):
    drug_name: str


class ClinicalTrialSearchRequest(BaseModel):
    condition: str
    phase: str | None = None
    status: str | None = None


class CitationRequest(BaseModel):
    pmids: list[str]
    format: str = "APA"


class SummarizeRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Topic or title for the source material")
    text: str = Field(..., min_length=1, description="Source text to summarize")


class KnowledgeGraphRequest(BaseModel):
    drug_name: str = Field(..., min_length=2)


class SafetyRequest(BaseModel):
    drug_name: str = Field(..., min_length=2)


class DocumentQARequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = 5


class RegulatoryRequest(BaseModel):
    drug_name: str = Field(..., min_length=2)


class ResearchPaperAnalysisRequest(BaseModel):
    pmid: str | None = None
    text: str | None = None


class DrugInteractionRequest(BaseModel):
    drug_a: str = Field(..., min_length=2)
    drug_b: str = Field(..., min_length=2)


class ComparativeAnalysisRequest(BaseModel):
    drug_names: list[str] = Field(..., min_length=2, max_length=4)


class WebSearchRAGRequest(BaseModel):
    query: str = Field(..., min_length=3)
    limit: int = 5


class PointsSummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    topic: str = Field(default="supplied text", min_length=1)
