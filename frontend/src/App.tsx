import { useState, type ComponentType } from "react";
import { Sidebar } from "./components/Sidebar";
import { NewsFeed } from "./components/NewsFeed";
import { GlobalRagWidget } from "./components/GlobalRagWidget";
import { LiteratureReviewPanel } from "./components/panels/LiteratureReviewPanel";
import { DrugDiscoveryPanel } from "./components/panels/DrugDiscoveryPanel";
import { ClinicalTrialsPanel } from "./components/panels/ClinicalTrialsPanel";
import { CitationGeneratorPanel } from "./components/panels/CitationGeneratorPanel";
import { ResearchSummarizerPanel } from "./components/panels/ResearchSummarizerPanel";
import { DocumentUploadPanel } from "./components/panels/DocumentUploadPanel";
import { KnowledgeGraphView } from "./components/panels/KnowledgeGraphView";
import { SafetyPanel } from "./components/panels/SafetyPanel";
import { ResearchDashboardPanel } from "./components/panels/ResearchDashboardPanel";
import { RegulatoryPanel } from "./components/panels/RegulatoryPanel";
import { PaperAnalyzerPanel } from "./components/panels/PaperAnalyzerPanel";
import { DrugInteractionPanel } from "./components/panels/DrugInteractionPanel";
import { ComparativeAnalysisPanel } from "./components/panels/ComparativeAnalysisPanel";

type View =
  | "news"
  | "dashboard"
  | "literature"
  | "papers"
  | "drugs"
  | "safety"
  | "interactions"
  | "regulatory"
  | "trials"
  | "compare"
  | "citations"
  | "summarize"
  | "documents"
  | "graph";

const AGENT_VIEWS: Record<Exclude<View, "news">, ComponentType> = {
  dashboard: ResearchDashboardPanel,
  literature: LiteratureReviewPanel,
  papers: PaperAnalyzerPanel,
  drugs: DrugDiscoveryPanel,
  safety: SafetyPanel,
  interactions: DrugInteractionPanel,
  regulatory: RegulatoryPanel,
  trials: ClinicalTrialsPanel,
  compare: ComparativeAnalysisPanel,
  citations: CitationGeneratorPanel,
  summarize: ResearchSummarizerPanel,
  documents: DocumentUploadPanel,
  graph: KnowledgeGraphView,
};

// The knowledge graph and dashboard need more horizontal room than a plain form-based panel.
const WIDE_VIEWS: View[] = ["graph", "dashboard"];

export default function App() {
  const [view, setView] = useState<View>("news");
  const ActiveAgent = view === "news" ? null : AGENT_VIEWS[view];

  return (
    <>
      <div className="watermark" aria-hidden="true" />
      <div className="app-shell">
        <Sidebar active={view} onSelect={(key) => setView(key as View)} />
        <main className="main-content">
          {ActiveAgent ? (
            <div className={`agent-view ${WIDE_VIEWS.includes(view) ? "agent-view-wide" : ""}`}>
              <ActiveAgent />
            </div>
          ) : (
            <NewsFeed />
          )}
        </main>
      </div>
      <GlobalRagWidget />
    </>
  );
}
