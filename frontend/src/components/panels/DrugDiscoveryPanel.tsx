import { useState, type FormEvent } from "react";
import { lookupDrug, type DrugDiscoveryResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function DrugDiscoveryPanel() {
  const [drugName, setDrugName] = useState("");
  const { loading, error, result, run } = useAgentCall<DrugDiscoveryResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!drugName.trim()) return;
    run(() => lookupDrug(drugName.trim()));
  }

  return (
    <PanelShell
      icon="💊"
      title="Drug Discovery"
      description="Pulls FDA label data and related compounds, then synthesizes candidates."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Drug name
          <input
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            placeholder="e.g. metformin"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Looking up…" : "Look up"}
        </button>
      </form>
      {loading && <p className="panel-hint">Querying openFDA and RxNav, then running local synthesis…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.mechanism_of_action || result.candidate_drugs.length > 0 ? (
            <>
              {result.mechanism_of_action && (
                <>
                  <h4>Mechanism of action</h4>
                  <p>{result.mechanism_of_action}</p>
                </>
              )}
              {result.comparison_report && (
                <>
                  <h4>Comparison report</h4>
                  <p>{result.comparison_report}</p>
                </>
              )}
              {result.candidate_drugs.length > 0 && (
                <>
                  <h4>Candidate drugs</h4>
                  <ul className="panel-chips">
                    {result.candidate_drugs.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.similar_compounds.length > 0 && (
                <>
                  <h4>Similar compounds</h4>
                  <ul className="panel-chips">
                    {result.similar_compounds.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No FDA label or related compound data found for this drug.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
