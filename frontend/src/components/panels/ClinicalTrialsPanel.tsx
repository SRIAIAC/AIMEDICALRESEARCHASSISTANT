import { useState, type FormEvent } from "react";
import { searchTrials, type ClinicalTrialResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function ClinicalTrialsPanel() {
  const [condition, setCondition] = useState("");
  const [phase, setPhase] = useState("");
  const [status, setStatus] = useState("");
  const { loading, error, result, run } = useAgentCall<ClinicalTrialResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!condition.trim()) return;
    run(() => searchTrials(condition.trim(), phase, status));
  }

  return (
    <PanelShell
      icon="🧪"
      title="Clinical Trial Analyzer"
      description="Reads ClinicalTrials.gov data to compare phases, populations, and outcomes."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Condition
          <input
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            placeholder="e.g. type 2 diabetes"
            required
          />
        </label>
        <label className="panel-form-narrow">
          Phase (optional)
          <input value={phase} onChange={(e) => setPhase(e.target.value)} placeholder="PHASE3" />
        </label>
        <label className="panel-form-narrow">
          Status (optional)
          <input
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            placeholder="RECRUITING"
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {loading && <p className="panel-hint">Fetching trial records and running local synthesis — can take a minute or two.</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.study_comparison.length > 0 ? (
            <>
              {result.trial_summary && (
                <>
                  <h4>Trial landscape</h4>
                  <p>{result.trial_summary}</p>
                </>
              )}
              {result.patient_population_analysis && (
                <>
                  <h4>Patient population</h4>
                  <p>{result.patient_population_analysis}</p>
                </>
              )}
              <h4>Status breakdown</h4>
              <p className="panel-badge-row">
                {Object.entries(result.success_rates).map(([status, count]) => (
                  <span className="panel-badge" key={status}>
                    {status}: {count}
                  </span>
                ))}
              </p>
              <h4>Studies ({result.study_comparison.length})</h4>
              <ul className="panel-sources">
                {result.study_comparison.slice(0, 10).map((s) => (
                  <li key={s.nct_id}>
                    <a href={`https://clinicaltrials.gov/study/${s.nct_id}`} target="_blank" rel="noreferrer">
                      {s.title}
                    </a>{" "}
                    <span className="panel-muted">
                      ({s.status}
                      {s.phase ? `, ${s.phase}` : ""}
                      {s.enrollment ? `, n=${s.enrollment}` : ""})
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="panel-empty">No trials found for this condition.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
