import { useState, type FormEvent } from "react";
import { checkRegulatory, type RegulatoryResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function RegulatoryPanel() {
  const [drugName, setDrugName] = useState("");
  const { loading, error, result, run } = useAgentCall<RegulatoryResult>();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!drugName.trim()) return;
    run(() => checkRegulatory(drugName.trim()));
  }

  return (
    <PanelShell
      icon="🏛️"
      title="Regulatory Intelligence"
      description="Tracks FDA approval history and recalls for a drug (openFDA drugsfda + enforcement)."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Drug name
          <input
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            placeholder="e.g. Keytruda"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Checking…" : "Check regulatory status"}
        </button>
      </form>
      {loading && <p className="panel-hint">Querying FDA approval and recall records, then running local synthesis…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && (
        <div className="panel-result">
          {result.regulatory_summary || result.approvals.length > 0 || result.recalls.length > 0 ? (
            <>
              {result.regulatory_summary && (
                <>
                  <h4>Regulatory summary</h4>
                  <p>{result.regulatory_summary}</p>
                </>
              )}
              {result.approval_timeline_summary && (
                <>
                  <h4>Approval timeline</h4>
                  <p>{result.approval_timeline_summary}</p>
                </>
              )}
              {result.recall_summary && (
                <>
                  <h4>Recalls</h4>
                  <p>{result.recall_summary}</p>
                </>
              )}
              {result.notable_flags.length > 0 && (
                <>
                  <h4>Notable flags</h4>
                  <ul>
                    {result.notable_flags.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.approvals.length > 0 && (
                <>
                  <h4>Approval records</h4>
                  <ul className="panel-sources">
                    {result.approvals.map((a, i) => (
                      <li key={i}>
                        <strong>{a.sponsor ?? "Unknown sponsor"}</strong> — {a.application_number}
                        <br />
                        <span className="panel-muted">
                          {a.dosage_form} {a.route ? `· ${a.route}` : ""} · {a.submission_count} submissions
                          {a.first_approval_date ? ` · first approved ${a.first_approval_date}` : ""}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {result.recalls.length > 0 && (
                <>
                  <h4>Recall records</h4>
                  <ul className="panel-sources">
                    {result.recalls.map((r, i) => (
                      <li key={i}>
                        <strong>
                          {r.classification} — {r.status}
                        </strong>
                        <br />
                        <span className="panel-muted">{r.reason}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">No FDA approval or recall records found for this drug.</p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
