import { useMemo, useState, type FormEvent } from "react";
import {
  fetchKnowledgeGraph,
  type GraphEdge,
  type GraphNode,
  type GraphNodeType,
  type KnowledgeGraphResult,
} from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

const NODE_COLORS: Record<string, string> = {
  drug: "#0f766e",
  target: "#7c3aed",
  protein: "#2563eb",
  gene: "#d97706",
  trial: "#db2777",
  disease: "#dc2626",
  paper: "#475569",
};

const NODE_RADIUS: Record<string, number> = {
  drug: 17,
  target: 12,
  protein: 10,
  gene: 10,
  trial: 9,
  disease: 9,
  paper: 8,
};

// The graph is really a fixed pipeline, not an arbitrary network: genes
// encode proteins, proteins make up targets, targets are acted on by the
// drug, and the drug leads to trials/papers, with trials leading to the
// diseases they study. Laying nodes out in columns that follow this order
// (instead of a force simulation) makes the direction of every relationship
// obvious at a glance, like a flowchart, and is fully deterministic.
const STAGE_ORDER: GraphNodeType[][] = [
  ["gene"],
  ["protein"],
  ["target"],
  ["drug"],
  ["trial", "paper"],
  ["disease"],
];

const COLUMN_WIDTH = 210;
const ROW_HEIGHT = 64;
const MARGIN_X = 90;
const MARGIN_Y = 36;

function truncate(label: string, max = 24): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

interface PositionedEdge {
  source: PositionedNode;
  target: PositionedNode;
  relation: string;
}

interface Layout {
  nodes: PositionedNode[];
  edges: PositionedEdge[];
  width: number;
  height: number;
}

function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): Layout {
  const presentTypes = new Set(nodes.map((n) => n.type));
  const stages = STAGE_ORDER.filter((types) => types.some((t) => presentTypes.has(t)));
  const typeToStage = new Map<GraphNodeType, number>();
  stages.forEach((types, i) => types.forEach((t) => typeToStage.set(t, i)));

  const byStage: GraphNode[][] = stages.map(() => []);
  for (const node of nodes) {
    const stageIndex = typeToStage.get(node.type);
    if (stageIndex !== undefined) byStage[stageIndex].push(node);
  }
  // Group same-type nodes together within a shared column (e.g. trial/paper).
  byStage.forEach((list) =>
    list.sort((a, b) => (a.type === b.type ? a.label.localeCompare(b.label) : a.type.localeCompare(b.type))),
  );

  const maxRows = Math.max(...byStage.map((list) => list.length), 1);
  const height = maxRows * ROW_HEIGHT + MARGIN_Y * 2;
  const width = MARGIN_X * 2 + Math.max(stages.length - 1, 0) * COLUMN_WIDTH;

  const positioned = new Map<string, PositionedNode>();
  byStage.forEach((list, stageIndex) => {
    const columnHeight = list.length * ROW_HEIGHT;
    const startY = (height - columnHeight) / 2 + ROW_HEIGHT / 2;
    const x = MARGIN_X + stageIndex * COLUMN_WIDTH;
    list.forEach((node, i) => {
      positioned.set(node.id, { ...node, x, y: startY + i * ROW_HEIGHT });
    });
  });

  const positionedNodes = [...positioned.values()];
  const positionedEdges: PositionedEdge[] = edges
    .map((e) => ({ source: positioned.get(e.source), target: positioned.get(e.target), relation: e.relation }))
    .filter((e): e is PositionedEdge => Boolean(e.source && e.target));

  return { nodes: positionedNodes, edges: positionedEdges, width, height };
}

// Trims a line to start/end at the edge of each node's circle (rather than
// its center) so arrowheads land right at the circle boundary.
function trimmedEdge(edge: PositionedEdge) {
  const { source, target } = edge;
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  const r1 = NODE_RADIUS[source.type] ?? 8;
  const r2 = (NODE_RADIUS[target.type] ?? 8) + 6;
  return {
    x1: source.x + ux * r1,
    y1: source.y + uy * r1,
    x2: target.x - ux * r2,
    y2: target.y - uy * r2,
  };
}

export function KnowledgeGraphView() {
  const [drugName, setDrugName] = useState("");
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const { loading, error, result, run } = useAgentCall<KnowledgeGraphResult>();

  const layout = useMemo(() => {
    if (!result) return null;
    return layoutGraph(result.nodes, result.edges);
  }, [result]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!drugName.trim()) return;
    setSelected(null);
    run(() => fetchKnowledgeGraph(drugName.trim()));
  }

  return (
    <PanelShell
      icon="🕸️"
      title="Knowledge Graph"
      description="Explores real Disease / Gene / Protein / Drug / Target / Clinical Trial / Research Paper relationships around a drug — built from ChEMBL, ClinicalTrials.gov, and PubMed, not LLM-generated."
    >
      <form onSubmit={handleSubmit} className="panel-form">
        <label>
          Drug name
          <input
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            placeholder="e.g. aspirin"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Building graph…" : "Explore"}
        </button>
      </form>
      {loading && <p className="panel-hint">Querying ChEMBL, ClinicalTrials.gov, and PubMed…</p>}
      {error && <p className="panel-error">{error}</p>}
      {result && layout && (
        <div className="graph-layout">
          {layout.nodes.length <= 1 ? (
            <p className="panel-empty">No relationships found for this drug.</p>
          ) : (
            <>
              <div className="graph-canvas-wrap">
                <svg width={layout.width} height={layout.height} className="graph-svg">
                  <defs>
                    <marker
                      id="graph-arrow"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="7"
                      markerHeight="7"
                      orient="auto-start-reverse"
                    >
                      <path d="M0,0 L10,5 L0,10 z" className="graph-arrow-head" />
                    </marker>
                  </defs>
                  {layout.edges.map((edge, i) => {
                    const { x1, y1, x2, y2 } = trimmedEdge(edge);
                    return (
                      <line
                        key={i}
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        className="graph-edge"
                        markerEnd="url(#graph-arrow)"
                      />
                    );
                  })}
                  {layout.nodes.map((node) => (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      className="graph-node"
                      onClick={() => setSelected(node)}
                    >
                      <circle
                        r={NODE_RADIUS[node.type] ?? 8}
                        fill={NODE_COLORS[node.type] ?? "#888"}
                        className={selected?.id === node.id ? "graph-node-selected" : ""}
                      />
                      <text y={(NODE_RADIUS[node.type] ?? 8) + 16} textAnchor="middle" className="graph-node-label">
                        {truncate(node.label)}
                      </text>
                      <title>{node.label}</title>
                    </g>
                  ))}
                </svg>
              </div>
              <div className="graph-sidebar">
                <div className="graph-legend">
                  {Object.entries(NODE_COLORS).map(([type, color]) => (
                    <span className="graph-legend-item" key={type}>
                      <span className="graph-legend-dot" style={{ background: color }} />
                      {type}
                    </span>
                  ))}
                </div>
                <div className="graph-details">
                  {selected ? (
                    <>
                      <span className="panel-badge">{selected.type}</span>
                      <p className="graph-details-label">{selected.label}</p>
                      {Object.entries(selected.meta).map(([key, value]) =>
                        value ? (
                          <p className="panel-muted" key={key}>
                            {key}: {String(value)}
                          </p>
                        ) : null,
                      )}
                      {selected.type === "paper" && typeof selected.meta.url === "string" && (
                        <a href={selected.meta.url} target="_blank" rel="noreferrer">
                          Open on PubMed
                        </a>
                      )}
                      {selected.type === "trial" && typeof selected.meta.nct_id === "string" && (
                        <a
                          href={`https://clinicaltrials.gov/study/${selected.meta.nct_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open on ClinicalTrials.gov
                        </a>
                      )}
                    </>
                  ) : (
                    <p className="panel-hint">Click a node to see its details.</p>
                  )}
                </div>
                <p className="panel-muted">
                  {result.nodes.length} nodes · {result.edges.length} edges
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </PanelShell>
  );
}
