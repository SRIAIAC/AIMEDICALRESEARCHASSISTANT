import { useState, type FormEvent } from "react";
import { summarizeText, type SummarizeResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function ResearchSummarizerPanel() {
  const [topic, setTopic] = useState("");
  const [text, setText] = useState("");
  const { loading, error, result, run } = useAgentCall<SummarizeResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!topic.trim() || !text.trim()) return;
    run(() => summarizeText(topic.trim(), text.trim()));
  }

  return (
    <PanelShell
      icon="📝"
      title="Research Summarizer"
      description="Summarizes supplied text into an executive summary and clinical implications."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Topic
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Metformin and longevity"
            required
          />
        </label>
        <label>
          Source text
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an abstract, paper excerpt, or notes to summarize…"
            rows={4}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Summarizing…" : "Summarize"}
        </button>
      </form>
      {loading && <p className="panel-hint">Running local synthesis — this can take a minute or two.</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.executive_summary ? (
            <>
              <h4>Executive summary</h4>
              <p>{result.executive_summary}</p>
              {result.one_page_summary && (
                <>
                  <h4>One-page summary</h4>
                  <p>{result.one_page_summary}</p>
                </>
              )}
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
              {result.clinical_implications.length > 0 && (
                <>
                  <h4>Clinical implications</h4>
                  <ul>
                    {result.clinical_implications.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No summary could be generated from the supplied text.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
