import { useState, type FormEvent } from "react";
import { checkSafety, type SafetyResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

function truncate(text: string, max = 500): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export function SafetyPanel() {
  const [drugName, setDrugName] = useState("");
  const { loading, error, result, run } = useAgentCall<SafetyResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!drugName.trim()) return;
    run(() => checkSafety(drugName.trim()));
  }

  return (
    <PanelShell
      icon="⚠️"
      title="Drug Safety & Pharmacovigilance"
      description="Checks FDA label safety sections and FAERS adverse-event reports — a research aid, not a clinical decision tool."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Drug name
          <input
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            placeholder="e.g. warfarin"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Checking…" : "Check safety"}
        </button>
      </form>
      {loading && <p className="panel-hint">Querying FDA labels and FAERS, then running local synthesis…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.safety_summary || result.top_adverse_events.length > 0 ? (
            <>
              <p className="panel-error">
                This is a research-support summary grounded in FDA/FAERS data — not a
                substitute for clinical judgment or a pharmacist/prescriber review.
              </p>
              {result.safety_summary && (
                <>
                  <h4>Safety summary</h4>
                  <p>{result.safety_summary}</p>
                </>
              )}
              {result.key_risks.length > 0 && (
                <>
                  <h4>Key risks</h4>
                  <ul>
                    {result.key_risks.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.notable_interactions.length > 0 && (
                <>
                  <h4>Notable interactions</h4>
                  <ul>
                    {result.notable_interactions.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.signal_assessment && (
                <>
                  <h4>FAERS signal assessment</h4>
                  <p>{result.signal_assessment}</p>
                </>
              )}
              {result.top_adverse_events.length > 0 && (
                <>
                  <h4>Top reported adverse events (FAERS, unverified reports)</h4>
                  <p className="panel-badge-row">
                    {result.top_adverse_events.map((ev) => (
                      <span className="panel-badge" key={ev.term}>
                        {ev.term.toLowerCase()}: {ev.count.toLocaleString()}
                      </span>
                    ))}
                  </p>
                </>
              )}
              {result.contraindications && (
                <>
                  <h4>Contraindications (from label)</h4>
                  <p className="panel-muted">{truncate(result.contraindications)}</p>
                </>
              )}
              {result.drug_interactions && (
                <>
                  <h4>Drug interactions (from label)</h4>
                  <p className="panel-muted">{truncate(result.drug_interactions)}</p>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No FDA label safety data or FAERS reports found for this drug.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
