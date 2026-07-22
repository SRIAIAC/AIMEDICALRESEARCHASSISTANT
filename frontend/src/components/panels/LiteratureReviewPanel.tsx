import { useState, type FormEvent } from "react";
import { searchLiterature, type LiteratureReviewResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function LiteratureReviewPanel() {
  const [topic, setTopic] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const { loading, error, result, run } = useAgentCall<LiteratureReviewResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;
    run(() => searchLiterature(topic.trim(), maxResults));
  }

  return (
    <PanelShell
      icon="📚"
      title="Literature Review"
      description="Searches PubMed and synthesizes a grounded systematic review."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Topic
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. metformin cardiovascular outcomes"
            required
          />
        </label>
        <label className="panel-form-narrow">
          Max results
          <input
            type="number"
            min={1}
            max={50}
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Searching PubMed…" : "Search"}
        </button>
      </form>
      {loading && <p className="panel-hint">Fetching abstracts and running local synthesis — this can take a minute or two.</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.summary ? (
            <>
              <p className="panel-badge-row">
                <span className="panel-badge">Evidence: {result.evidence_level ?? "—"}</span>
              </p>
              <p>{result.summary}</p>
              {result.key_findings.length > 0 && (
                <>
                  <h4>Key findings</h4>
                  <ul>
                    {result.key_findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.conclusions.length > 0 && (
                <>
                  <h4>Conclusions</h4>
                  <ul>
                    {result.conclusions.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.sources.length > 0 && (
                <>
                  <h4>Sources ({result.sources.length})</h4>
                  <ul className="panel-sources">
                    {result.sources.map((s) => (
                      <li key={s.pmid}>
                        <a href={s.url} target="_blank" rel="noreferrer">
                          {s.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No PubMed results found for this topic.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
