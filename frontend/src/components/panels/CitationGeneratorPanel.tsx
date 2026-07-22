import { useState, type FormEvent } from "react";
import { generateCitations, type CitationResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

const FORMATS = ["APA", "MLA", "Vancouver", "IEEE", "Nature"];

export function CitationGeneratorPanel() {
  const [pmids, setPmids] = useState("");
  const [format, setFormat] = useState("APA");
  const { loading, error, result, run } = useAgentCall<CitationResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const ids = pmids
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    if (ids.length === 0) return;
    run(() => generateCitations(ids, format));
  }

  return (
    <PanelShell
      icon="📑"
      title="Citation Generator"
      description="Formats PubMed references into a bibliography — no LLM involved, pure formatting."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          PMIDs (comma-separated)
          <input
            value={pmids}
            onChange={(e) => setPmids(e.target.value)}
            placeholder="e.g. 31978945, 32109013"
            required
          />
        </label>
        <label className="panel-form-narrow">
          Format
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            {FORMATS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Generating…" : "Generate"}
        </button>
      </form>
      {loading && <p className="panel-hint">Fetching reference metadata from PubMed…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.bibliography.length > 0 ? (
            <>
              <h4>Bibliography ({result.format})</h4>
              <ol className="panel-bibliography">
                {result.bibliography.map((entry, i) => (
                  <li key={i}>{entry}</li>
                ))}
              </ol>
              {result.inline_citations.length > 0 && (
                <>
                  <h4>Inline citations</h4>
                  <p className="panel-badge-row">
                    {result.inline_citations.map((c, i) => (
                      <span className="panel-badge" key={i}>
                        {c}
                      </span>
                    ))}
                  </p>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No matching references found for those PMIDs.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
