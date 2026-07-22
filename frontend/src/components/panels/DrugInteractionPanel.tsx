import { useState, type FormEvent } from "react";
import { checkInteraction, type DrugInteractionResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function DrugInteractionPanel() {
  const [drugA, setDrugA] = useState("");
  const [drugB, setDrugB] = useState("");
  const { loading, error, result, run } = useAgentCall<DrugInteractionResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!drugA.trim() || !drugB.trim()) return;
    run(() => checkInteraction(drugA.trim(), drugB.trim()));
  }

  return (
    <PanelShell
      icon="🔀"
      title="Drug-Drug Interaction Checker"
      description="Cross-references two drugs' FDA label text for a plausible interaction. This is a text-based label comparison, not a query against a dedicated drug-interaction database — always verify with a pharmacist."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Drug A
          <input value={drugA} onChange={(e) => setDrugA(e.target.value)} placeholder="e.g. warfarin" required />
        </label>
        <label>
          Drug B
          <input value={drugB} onChange={(e) => setDrugB(e.target.value)} placeholder="e.g. aspirin" required />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Checking…" : "Check interaction"}
        </button>
      </form>
      {loading && <p className="panel-hint">Fetching both labels and cross-referencing…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.interaction_found !== null ? (
            <>
              <p className="panel-badge-row">
                <span className="panel-badge">
                  {result.interaction_found ? "Plausible interaction" : "No interaction indicated"}
                </span>
                {result.risk_level && <span className="panel-badge">risk: {result.risk_level}</span>}
              </p>
              {result.explanation && (
                <>
                  <h4>Explanation</h4>
                  <p>{result.explanation}</p>
                </>
              )}
              {result.recommendation && (
                <>
                  <h4>Recommendation</h4>
                  <p>{result.recommendation}</p>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">
              Neither drug's label had interaction text to compare — try different drug names.
            </p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
