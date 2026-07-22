import type { ResearchReportResult } from "../api";

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item))).join(", ");
  }
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export function buildReportMarkdown(result: ResearchReportResult): string {
  const lines: string[] = [];
  lines.push(`# Research Report: ${result.query}`);
  lines.push(`\n_Generated ${new Date().toLocaleString()}_\n`);

  const failedNames = Object.keys(result.failed_agents);
  if (failedNames.length > 0) {
    lines.push("## Failed stages\n");
    for (const name of failedNames) {
      lines.push(`- **${name}**: ${result.failed_agents[name]}`);
    }
    lines.push("");
  }

  const synthesis = result.evidence_synthesis;
  if (synthesis) {
    lines.push("## Evidence Synthesis\n");
    if (synthesis.evidence_strength) lines.push(`**Evidence strength:** ${synthesis.evidence_strength}\n`);
    if (synthesis.overall_assessment) lines.push(`${synthesis.overall_assessment}\n`);
    if (synthesis.consensus_points.length > 0) {
      lines.push("### Consensus points");
      synthesis.consensus_points.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (synthesis.conflicting_findings.length > 0) {
      lines.push("### Conflicting findings");
      synthesis.conflicting_findings.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (synthesis.research_gaps.length > 0) {
      lines.push("### Research gaps");
      synthesis.research_gaps.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
  }

  const verification = result.citation_verification;
  if (verification) {
    lines.push("## Citation Verification\n");
    if (verification.verification_summary) lines.push(`${verification.verification_summary}\n`);
    if (verification.verified_claims.length > 0) {
      lines.push("### Verified claims");
      verification.verified_claims.forEach((vc) => lines.push(`- ${vc.claim} _(source: ${vc.supporting_source})_`));
      lines.push("");
    }
    if (verification.unsupported_claims.length > 0) {
      lines.push("### ⚠ Unsupported claims (could not be traced to a retrieved source)");
      verification.unsupported_claims.forEach((c) => lines.push(`- ${c}`));
      lines.push("");
    }
  }

  lines.push("## Specialist Agent Findings\n");
  for (const [name, data] of Object.entries(result.agents)) {
    lines.push(`### ${name.replace(/_/g, " ")}\n`);
    for (const [key, value] of Object.entries(data)) {
      if (key === "agent" || key === "query" || value === null || value === undefined) continue;
      if (Array.isArray(value) && value.length === 0) continue;
      lines.push(`**${key.replace(/_/g, " ")}:** ${formatValue(value)}\n`);
    }
  }

  lines.push(
    "---\n_Research-support summary only — not a substitute for clinical judgment. Verify all claims against the original sources before relying on them._",
  );

  return lines.join("\n");
}

export function downloadTextFile(filename: string, content: string, mimeType = "text/markdown;charset=utf-8"): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
