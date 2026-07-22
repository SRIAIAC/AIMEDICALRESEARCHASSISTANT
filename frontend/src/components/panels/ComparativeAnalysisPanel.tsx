import { useState, type FormEvent } from "react";
import { compareDrugs, type ComparativeAnalysisResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

const MAX_DRUGS = 4;

function formatKey(key: string): string {
  return key.replace(/_/g, " ");
}

export function ComparativeAnalysisPanel() {
  const [drugNames, setDrugNames] = useState(["", ""]);
  const { loading, error, result, run } = useAgentCall<ComparativeAnalysisResult>();

  function updateDrug(index: number, value: string) {
    setDrugNames((prev) => prev.map((d, i) => (i === index ? value : d)));
  }

  function addDrug() {
    if (drugNames.length < MAX_DRUGS) setDrugNames((prev) => [...prev, ""]);
  }

  function removeDrug(index: number) {
    setDrugNames((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const names = drugNames.map((d) => d.trim()).filter(Boolean);
    if (names.length < 2) return;
    run(() => compareDrugs(names));
  }

  return (
    <PanelShell
      icon="⚖️"
      title="Comparative Research Analysis"
      description="Compares 2-4 drugs side-by-side across mechanism, indications, and safety, grounded in their FDA labels."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        {drugNames.map((name, i) => (
          <label key={i} className="panel-form-narrow">
            Drug {i + 1}
            <span className="drug-input-row">
              <input value={name} onChange={(e) => updateDrug(i, e.target.value)} placeholder="drug name" />
              {drugNames.length > 2 && (
                <button type="button" className="document-copy-btn" onClick={() => removeDrug(i)}>
                  ✕
                </button>
              )}
            </span>
          </label>
        ))}
        {drugNames.length < MAX_DRUGS && (
          <button type="button" className="document-copy-btn" onClick={addDrug}>
            + Add drug
          </button>
        )}
        <button type="submit" disabled={loading}>
          {loading ? "Comparing…" : "Compare"}
        </button>
      </form>
      {loading && <p className="panel-hint">Fetching each drug's label data, then running local synthesis…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.comparison_summary ? (
            <>
              <p>{result.comparison_summary}</p>
              {result.efficacy_comparison && (
                <>
                  <h4>Efficacy comparison</h4>
                  <p>{result.efficacy_comparison}</p>
                </>
              )}
              {result.safety_comparison && (
                <>
                  <h4>Safety comparison</h4>
                  <p>{result.safety_comparison}</p>
                </>
              )}
              {result.comparison_table.length > 0 && (
                <>
                  <h4>Side-by-side</h4>
                  <div className="comparison-grid">
                    {result.comparison_table.map((row, i) => (
                      <div className="comparison-card" key={i}>
                        {Object.entries(row).map(([key, value]) => (
                          <div key={key}>
                            <strong>{formatKey(key)}:</strong>{" "}
                            {Array.isArray(value) ? value.join(", ") || "—" : String(value ?? "—")}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No FDA label data found for these drugs.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
