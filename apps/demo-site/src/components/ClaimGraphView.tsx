import { useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { ComponentProps } from "react";
import type { ElementDefinition } from "cytoscape";
import { RUN_CASES, useBundle } from "../data";

const STYLE: NonNullable<ComponentProps<typeof CytoscapeComponent>["stylesheet"]> = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 9,
      "text-wrap": "wrap",
      "text-max-width": "90px",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 4,
      "border-width": 1,
      "border-color": "#94a3b8",
      "background-color": "#e2e8f0",
    },
  },
  {
    selector: "node.claim",
    style: {
      "background-color": "#3b82f6",
      "border-color": "#1d4ed8",
      color: "#1e293b",
      "font-weight": 600,
    },
  },
  {
    selector: "node.claim.supported",
    style: { "background-color": "#22c55e", "border-color": "#15803d" },
  },
  {
    selector: "node.claim.unsupported",
    style: { "background-color": "#ef4444", "border-color": "#b91c1c" },
  },
  {
    selector: "node.claim.qualified",
    style: { "background-color": "#f59e0b", "border-color": "#b45309" },
  },
  {
    selector: "node.source",
    style: {
      shape: "round-rectangle",
      "background-color": "#64748b",
      "border-color": "#334155",
      color: "#f8fafc",
      "text-max-width": "120px",
      "font-size": 8,
    },
  },
  {
    selector: "node.evidence",
    style: {
      shape: "diamond",
      "background-color": "#a78bfa",
      "border-color": "#7c3aed",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.2,
      "line-color": "#cbd5e1",
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "target-arrow-color": "#cbd5e1",
      "arrow-scale": 0.7,
      label: "data(label)",
      "font-size": 7,
      color: "#64748b",
      "text-rotation": "autorotate",
    },
  },
  {
    selector: "edge.grounded",
    style: { "line-color": "#22c55e", "target-arrow-color": "#22c55e" },
  },
  {
    selector: "edge.weak",
    style: { "line-color": "#f59e0b", "target-arrow-color": "#f59e0b", "line-style": "dashed" },
  },
];

export function ClaimGraphView({
  selectedRun,
  onSelectRun,
}: {
  selectedRun: string;
  onSelectRun: (id: string) => void;
}) {
  const active = RUN_CASES.find((c) => c.id === selectedRun) ?? RUN_CASES[0];
  const bundle = useBundle(active.bundlePath);

  const elements = useMemo<
    ComponentProps<typeof CytoscapeComponent>["elements"]
  >(() => {
    if (!bundle) return [];
    const els: ElementDefinition[] = [];
    const seenClaims = new Set<string>();
    const seenSources = new Set<string>();
    const seenEvidence = new Set<string>();

    for (const claim of bundle.claims) {
      if (seenClaims.has(claim.claim_id)) continue;
      seenClaims.add(claim.claim_id);
      els.push({
        data: {
          id: claim.claim_id,
          label: claim.text.slice(0, 60) + (claim.text.length > 60 ? "…" : ""),
        },
        classes: `claim ${claim.status ?? ""}`,
      });
    }

    for (const frag of bundle.evidence_fragments) {
      if (seenEvidence.has(frag.evidence_id)) continue;
      seenEvidence.add(frag.evidence_id);
      els.push({ data: { id: frag.evidence_id, label: "evidence" }, classes: "evidence" });
    }

    for (const source of bundle.sources) {
      if (seenSources.has(source.source_id)) continue;
      seenSources.add(source.source_id);
      els.push({
        data: { id: source.source_id, label: (source.title ?? source.canonical_uri ?? "").slice(0, 70) },
        classes: "source",
      });
    }

    for (const edge of bundle.claim_support_edges) {
      const strong = edge.grounding_status === "grounded" && (edge.confidence ?? 0) >= 0.5;
      els.push({
        data: {
          id: edge.edge_id,
          source: edge.claim_id,
          target: edge.evidence_id ?? edge.source_id,
          label: `${edge.relation ?? "edge"} ${edge.confidence ?? ""}`,
        },
        classes: strong ? "grounded" : "weak",
      });
    }

    for (const frag of bundle.evidence_fragments) {
      if (!frag.source_id) continue;
      els.push({
        data: { id: `${frag.evidence_id}-src`, source: frag.evidence_id, target: frag.source_id, label: "" },
      });
    }

    return els;
  }, [bundle]);

  return (
    <div className="page">
      <h2>Claim Graph</h2>
      <p className="page-note">
        Every claim node is connected to the evidence it relies on; edges are typed
        (supported / context_only / contradicted) with confidence. Green edges are grounded in the
        frozen corpus — red claims carry no support and are blocked by the audit gate.
      </p>
      <div className="run-selector">
        {RUN_CASES.map((c) => (
          <button
            key={c.id}
            className={`run-btn${c.id === selectedRun ? " active" : ""}`}
            onClick={() => onSelectRun(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>
      <div className="graph-legend">
        <span><span className="dot claim"></span> claim</span>
        <span><span className="dot supported"></span> supported</span>
        <span><span className="dot unsupported"></span> unsupported</span>
        <span><span className="dot evidence"></span> evidence</span>
        <span><span className="dot source"></span> source</span>
      </div>
      {bundle ? (
        <div className="graph-container">
          <CytoscapeComponent
            elements={elements}
            style={{ width: "100%", height: "640px" }}
            stylesheet={STYLE}
            layout={{ name: "cose", animate: false, padding: 30, nodeRepulsion: 4000 }}
            wheelSensitivity={0.3}
          />
        </div>
      ) : (
        <p className="muted">Loading…</p>
      )}
    </div>
  );
}
