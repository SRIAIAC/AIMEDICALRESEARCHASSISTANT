import { useState, type FormEvent } from "react";
import { analyzePaper, type PaperAnalysisResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function PaperAnalyzerPanel() {
  const [pmid, setPmid] = useState("");
  const [text, setText] = useState("");
  const { loading, error, result, run } = useAgentCall<PaperAnalysisResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!pmid.trim() && !text.trim()) return;
    run(() => analyzePaper({ pmid: pmid.trim() || undefined, text: text.trim() || undefined }));
  }

  return (
    <PanelShell
      icon="🔬"
      title="Research Paper Analyzer"
      description="Extracts objectives, methodology, population, endpoints, results, statistics, limitations, and conclusions from a single paper — by PMID or pasted text."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          PMID (optional if pasting text below)
          <input value={pmid} onChange={(e) => setPmid(e.target.value)} placeholder="e.g. 31978945" />
        </label>
        <label>
          Or paste paper text
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an abstract or full text not on PubMed…"
            rows={4}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </form>
      {loading && <p className="panel-hint">Running local extraction — a few seconds to a minute.</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          <h4>{result.title}</h4>
          {result.objectives || result.methodology || result.results || result.conclusions ? (
            <>
              {result.objectives && (
                <>
                  <h4>Objectives</h4>
                  <p>{result.objectives}</p>
                </>
              )}
              {result.methodology && (
                <>
                  <h4>Methodology</h4>
                  <p>{result.methodology}</p>
                </>
              )}
              {result.patient_population && (
                <>
                  <h4>Patient population</h4>
                  <p>{result.patient_population}</p>
                </>
              )}
              {result.interventions.length > 0 && (
                <>
                  <h4>Interventions</h4>
                  <ul>
                    {result.interventions.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.endpoints.length > 0 && (
                <>
                  <h4>Endpoints</h4>
                  <ul>
                    {result.endpoints.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.results && (
                <>
                  <h4>Results</h4>
                  <p>{result.results}</p>
                </>
              )}
              {result.statistical_findings && result.statistical_findings.length > 0 && (
                <>
                  <h4>Statistical findings</h4>
                  <ul>
                    {result.statistical_findings.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.limitations && result.limitations.length > 0 && (
                <>
                  <h4>Limitations</h4>
                  <ul>
                    {result.limitations.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.conclusions && (
                <>
                  <h4>Conclusions</h4>
                  <p>{result.conclusions}</p>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">
              No structured elements could be extracted — this abstract may not follow a
              typical clinical-trial structure.
            </p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
