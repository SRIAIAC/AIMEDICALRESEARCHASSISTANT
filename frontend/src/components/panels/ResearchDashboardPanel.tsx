import { useState, type FormEvent } from "react";
import { runResearch, type ResearchReportResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";
import { buildReportMarkdown, downloadTextFile } from "../../utils/reportMarkdown";

const AGENT_LABELS: Record<string, string> = {
  literature_review: "📚 Literature Review",
  drug_discovery: "💊 Drug Discovery",
  clinical_trial_analyzer: "🧪 Clinical Trial Analyzer",
  citation_generator: "📑 Citation Generator",
  research_summarizer: "📝 Research Summarizer",
  safety: "⚠️ Drug Safety",
  regulatory: "🏛️ Regulatory Intelligence",
};

const STRENGTH_ORDER = ["insufficient", "limited", "moderate", "strong"];

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

function AgentDetail({ name, data }: { name: string; data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(
    ([key, value]) =>
      key !== "agent" &&
      key !== "query" &&
      value !== null &&
      !(Array.isArray(value) && value.length === 0),
  );

  return (
    <details className="dashboard-agent-detail">
      <summary>{AGENT_LABELS[name] ?? name}</summary>
      <div className="panel-result">
        {entries.length === 0 && <p className="panel-empty">No findings.</p>}
        {entries.map(([key, value]) => (
          <div key={key}>
            <h4>{key.replace(/_/g, " ")}</h4>
            {Array.isArray(value) ? (
              <ul>
                {value.map((item, i) => (
                  <li key={i}>{typeof item === "object" ? JSON.stringify(item) : String(item)}</li>
                ))}
              </ul>
            ) : (
              <p>{typeof value === "object" ? JSON.stringify(value) : String(value)}</p>
            )}
          </div>
        ))}
      </div>
    </details>
  );
}

export function ResearchDashboardPanel() {
  const [query, setQuery] = useState("");
  const { loading, error, result, run } = useAgentCall<ResearchReportResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    run(() => runResearch(query.trim()));
  }

  const synthesis = result?.evidence_synthesis;
  const verification = result?.citation_verification;
  const failedCount = result ? Object.keys(result.failed_agents).length : 0;

  function handleDownload() {
    if (!result) return;
    const slug = result.query.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 60);
    downloadTextFile(`research-report-${slug || "untitled"}.md`, buildReportMarkdown(result));
  }

  return (
    <PanelShell
      icon="🧭"
      title="Research Dashboard"
      description="Runs all specialist agents on one query, then synthesizes their findings and checks the synthesis's claims against the actual retrieved sources — the full multi-agent pipeline in one place."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Research question
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. metformin for type 2 diabetes"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Running full pipeline…" : "Run research"}
        </button>
      </form>
      {loading && (
        <p className="panel-hint">
          Running 6 specialist agents, then evidence synthesis and citation verification — this runs several
          local LLM calls in sequence, so it can take several minutes.
        </p>
      )}
      {error && <p className="panel-error">{error}</p>}

      {result && (
        <div className="panel-result dashboard-report">
          <button type="button" className="document-copy-btn" onClick={handleDownload}>
            ⬇ Download report (Markdown)
          </button>
          {failedCount > 0 && (
            <p className="panel-error">
              {failedCount} stage{failedCount === 1 ? "" : "s"} failed and were skipped:{" "}
              {Object.keys(result.failed_agents).join(", ")}. Remaining results below are still shown.
            </p>
          )}

          {synthesis && (
            <div className="dashboard-synthesis">
              <h3>Evidence Synthesis</h3>
              {synthesis.evidence_strength && (
                <p className="panel-badge-row">
                  <span
                    className={`panel-badge dashboard-strength-${synthesis.evidence_strength}`}
                    title={`Strength rank: ${STRENGTH_ORDER.indexOf(synthesis.evidence_strength) + 1}/4`}
                  >
                    evidence strength: {synthesis.evidence_strength}
                  </span>
                </p>
              )}
              {asString(synthesis.overall_assessment) && <p>{synthesis.overall_assessment}</p>}
              {asStringArray(synthesis.consensus_points).length > 0 && (
                <>
                  <h4>Consensus points</h4>
                  <ul>
                    {synthesis.consensus_points.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
              {asStringArray(synthesis.conflicting_findings).length > 0 && (
                <>
                  <h4>Conflicting findings</h4>
                  <ul>
                    {synthesis.conflicting_findings.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
              {asStringArray(synthesis.research_gaps).length > 0 && (
                <>
                  <h4>Research gaps</h4>
                  <ul>
                    {synthesis.research_gaps.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {verification && (
            <div className="dashboard-verification">
              <h3>Citation Verification</h3>
              {asString(verification.verification_summary) && <p>{verification.verification_summary}</p>}
              {verification.verified_claims.length > 0 && (
                <>
                  <h4>Verified claims</h4>
                  <ul>
                    {verification.verified_claims.map((vc, i) => (
                      <li key={i}>
                        {vc.claim} <span className="panel-muted">— {vc.supporting_source}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {verification.unsupported_claims.length > 0 && (
                <>
                  <h4>⚠ Unsupported claims</h4>
                  <ul>
                    {verification.unsupported_claims.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          <h3 className="dashboard-section-title">Specialist agent findings</h3>
          <div className="dashboard-agents">
            {Object.entries(result.agents).map(([name, data]) => (
              <AgentDetail key={name} name={name} data={data} />
            ))}
          </div>
        </div>
      )}
    </PanelShell>
  );
}
