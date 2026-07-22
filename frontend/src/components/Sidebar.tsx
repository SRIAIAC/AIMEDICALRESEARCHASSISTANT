export interface AgentDef {
  key: string;
  icon: string;
  label: string;
}

export const AGENTS: AgentDef[] = [
  { key: "dashboard", icon: "🧭", label: "Research Dashboard" },
  { key: "literature", icon: "📚", label: "Literature Review" },
  { key: "papers", icon: "🔬", label: "Research Paper Analyzer" },
  { key: "drugs", icon: "💊", label: "Drug Discovery" },
  { key: "safety", icon: "⚠️", label: "Drug Safety" },
  { key: "interactions", icon: "🔀", label: "Drug Interaction Checker" },
  { key: "regulatory", icon: "🏛️", label: "Regulatory Intelligence" },
  { key: "trials", icon: "🧪", label: "Clinical Trial Analyzer" },
  { key: "compare", icon: "⚖️", label: "Comparative Analysis" },
  { key: "citations", icon: "📑", label: "Citation Generator" },
  { key: "summarize", icon: "📝", label: "Research Summarizer" },
  { key: "documents", icon: "📄", label: "Document Upload & Q&A" },
  { key: "graph", icon: "🕸️", label: "Knowledge Graph" },
];

export function Sidebar({ active, onSelect }: { active: string; onSelect: (key: string) => void }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>AI Medical Research Assistant</h1>
      </div>
      <nav className="sidebar-nav">
        <button
          type="button"
          className={`sidebar-nav-item ${active === "news" ? "active" : ""}`}
          onClick={() => onSelect("news")}
        >
          <span className="sidebar-nav-icon" aria-hidden="true">
            📰
          </span>
          <span>Latest News</span>
        </button>
        {AGENTS.map((agent) => (
          <button
            key={agent.key}
            type="button"
            className={`sidebar-nav-item ${active === agent.key ? "active" : ""}`}
            onClick={() => onSelect(agent.key)}
          >
            <span className="sidebar-nav-icon" aria-hidden="true">
              {agent.icon}
            </span>
            <span>{agent.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
