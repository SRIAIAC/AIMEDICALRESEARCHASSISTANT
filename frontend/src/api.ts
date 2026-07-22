const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8010";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BACKEND_URL}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle<T>(res);
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BACKEND_URL}/api/v1${path}`);
  return handle<T>(res);
}

async function upload<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BACKEND_URL}/api/v1${path}`, { method: "POST", body: formData });
  return handle<T>(res);
}

export interface LiteratureSource {
  pmid: string;
  title: string;
  url: string;
}

export interface LiteratureReviewResult {
  agent: string;
  query: string;
  summary: string | null;
  key_findings: string[];
  evidence_level: string | null;
  conclusions: string[];
  sources: LiteratureSource[];
}

export function searchLiterature(topic: string, maxResults: number) {
  return post<LiteratureReviewResult>("/literature/search", { topic, max_results: maxResults });
}

export interface DrugDiscoveryResult {
  agent: string;
  query: string;
  candidate_drugs: string[];
  mechanism_of_action: string | null;
  similar_compounds: string[];
  comparison_report: string | null;
}

export function lookupDrug(drugName: string) {
  return post<DrugDiscoveryResult>("/drugs/lookup", { drug_name: drugName });
}

export interface TrialStudy {
  nct_id: string;
  title: string;
  status: string;
  phase: string | null;
  enrollment: number | null;
  eligibility_criteria: string | null;
  min_age: string | null;
  max_age: string | null;
  start_date: string | null;
  completion_date: string | null;
}

export interface ClinicalTrialResult {
  agent: string;
  query: string;
  trial_summary: string | null;
  success_rates: Record<string, number>;
  study_comparison: TrialStudy[];
  patient_population_analysis: string | null;
  timeline: Array<{ nct_id: string; start_date: string | null; completion_date: string | null }>;
}

export function searchTrials(condition: string, phase: string, status: string) {
  return post<ClinicalTrialResult>("/trials/search", {
    condition,
    phase: phase.trim() || null,
    status: status.trim() || null,
  });
}

export interface CitationResult {
  agent: string;
  query: string;
  format: string;
  bibliography: string[];
  inline_citations: string[];
  doi_links: string[];
}

export function generateCitations(pmids: string[], format: string) {
  return post<CitationResult>("/citations/generate", { pmids, format });
}

export interface SummarizeResult {
  agent: string;
  query: string;
  one_page_summary: string | null;
  executive_summary: string | null;
  key_findings: string[];
  clinical_implications: string[];
}

export function summarizeText(query: string, text: string) {
  return post<SummarizeResult>("/summarize", { query, text });
}

export interface NewsItem {
  category: "announcement" | "breakthrough" | "drug_discovery";
  title: string;
  url: string;
  source: string;
  summary: string | null;
  date: string | null;
}

export interface NewsFeedResult {
  announcement: NewsItem[];
  breakthrough: NewsItem[];
  drug_discovery: NewsItem[];
  fetched_at: string;
  errors: Record<string, string>;
}

export function fetchNews() {
  return get<NewsFeedResult>("/news");
}

export interface DocumentUploadResult {
  doc_id: string;
  filename: string;
  page_count: number;
  ocr_pages: number[];
  chunks_indexed: number;
  text: string;
}

export function uploadDocument(file: File) {
  return upload<DocumentUploadResult>("/documents/upload", file);
}

export type GraphNodeType = "drug" | "target" | "protein" | "gene" | "trial" | "disease" | "paper";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  meta: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface KnowledgeGraphResult {
  agent: string;
  query: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function fetchKnowledgeGraph(drugName: string) {
  return post<KnowledgeGraphResult>("/knowledge-graph", { drug_name: drugName });
}

export interface AdverseEvent {
  term: string;
  count: number;
}

export interface SafetyResult {
  agent: string;
  query: string;
  safety_summary: string | null;
  key_risks: string[];
  notable_interactions: string[];
  signal_assessment: string | null;
  contraindications: string | null;
  drug_interactions: string | null;
  top_adverse_events: AdverseEvent[];
}

export function checkSafety(drugName: string) {
  return post<SafetyResult>("/safety/check", { drug_name: drugName });
}

export interface DocumentSource {
  id: string;
  label: string;
  source_type: string;
  excerpt: string;
}

export interface DocumentQAResult {
  agent: string;
  query: string;
  answer: string | null;
  supporting_sources: string[];
  confidence: "high" | "medium" | "low" | null;
  sources: DocumentSource[];
}

export function askDocuments(question: string, topK = 5) {
  return post<DocumentQAResult>("/documents/ask", { question, top_k: topK });
}

export interface EvidenceSynthesisResult {
  agent: string;
  query: string;
  overall_assessment: string | null;
  consensus_points: string[];
  conflicting_findings: string[];
  evidence_strength: "strong" | "moderate" | "limited" | "insufficient" | null;
  research_gaps: string[];
}

export interface VerifiedClaim {
  claim: string;
  supporting_source: string;
}

export interface CitationVerificationResult {
  agent: string;
  query: string;
  verified_claims: VerifiedClaim[];
  unsupported_claims: string[];
  verification_summary: string | null;
}

export interface ResearchReportResult {
  query: string;
  agents: Record<string, Record<string, unknown>>;
  evidence_synthesis: EvidenceSynthesisResult | null;
  citation_verification: CitationVerificationResult | null;
  failed_agents: Record<string, string>;
}

export function runResearch(query: string) {
  return post<ResearchReportResult>("/research", { query });
}

export interface ApprovalRecord {
  sponsor: string | null;
  application_number: string | null;
  brand_name: string | null;
  dosage_form: string | null;
  route: string | null;
  marketing_status: string | null;
  submission_count: number;
  first_approval_date: string | null;
  latest_submission_date: string | null;
  latest_submission_type: string | null;
}

export interface RecallRecord {
  recall_number: string | null;
  status: string | null;
  classification: string | null;
  reason: string | null;
  product_description: string | null;
  recall_initiation_date: string | null;
  voluntary_mandated: string | null;
}

export interface RegulatoryResult {
  agent: string;
  query: string;
  regulatory_summary: string | null;
  approval_timeline_summary: string | null;
  recall_summary: string | null;
  notable_flags: string[];
  approvals: ApprovalRecord[];
  recalls: RecallRecord[];
}

export function checkRegulatory(drugName: string) {
  return post<RegulatoryResult>("/regulatory/check", { drug_name: drugName });
}

export interface PaperAnalysisResult {
  agent: string;
  query: string;
  title: string;
  objectives: string | null;
  methodology: string | null;
  patient_population: string | null;
  interventions: string[];
  endpoints: string[];
  results: string | null;
  statistical_findings: string[] | null;
  limitations: string[] | null;
  conclusions: string | null;
}

export function analyzePaper(input: { pmid?: string; text?: string }) {
  return post<PaperAnalysisResult>("/papers/analyze", input);
}

export interface DrugInteractionResult {
  agent: string;
  query: string;
  drug_a: string;
  drug_b: string;
  interaction_found: boolean | null;
  risk_level: "high" | "moderate" | "low" | "unclear" | null;
  explanation: string | null;
  recommendation: string | null;
}

export function checkInteraction(drugA: string, drugB: string) {
  return post<DrugInteractionResult>("/interactions/check", { drug_a: drugA, drug_b: drugB });
}

export interface ComparativeAnalysisResult {
  agent: string;
  query: string;
  drug_names: string[];
  comparison_summary: string | null;
  comparison_table: Record<string, unknown>[];
  efficacy_comparison: string | null;
  safety_comparison: string | null;
}

export function compareDrugs(drugNames: string[]) {
  return post<ComparativeAnalysisResult>("/compare/drugs", { drug_names: drugNames });
}

export interface WebSearchSource {
  title: string;
  url: string;
  source: string;
}

export interface WebSearchRAGResult {
  agent: string;
  query: string;
  answer: string | null;
  key_points: string[];
  supporting_sources: string[];
  confidence: "high" | "medium" | "low" | null;
  sources: WebSearchSource[];
}

export function webSearchRAG(query: string, limit = 5) {
  return post<WebSearchRAGResult>("/rag/websearch", { query, limit });
}

export interface PointsSummaryResult {
  agent: string;
  query: string;
  title: string | null;
  points: string[];
  key_takeaway: string | null;
}

export function summarizePoints(text: string, topic: string) {
  return post<PointsSummaryResult>("/rag/summarize-points", { text, topic });
}
