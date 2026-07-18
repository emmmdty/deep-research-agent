import CytoscapeComponent from "react-cytoscapejs";
import type { ComponentProps } from "react";

import type { GraphEdge, GraphNode } from "../../types";

const nodeId = (node: GraphNode) => node.node_id ?? node.id ?? node.label;
const edgeId = (edge: GraphEdge, index: number) => edge.edge_id ?? edge.id ?? `edge-${index}`;
const graphStyles = [
  { selector: "node", style: { "background-color": "#087E6D", color: "#18201D", label: "data(label)", "font-size": 11, "text-wrap": "wrap", "text-max-width": 120, "text-valign": "bottom", "text-margin-y": 8, width: 28, height: 28 } },
  { selector: "node[kind = 'claim']", style: { "background-color": "#F7F8F6", "border-color": "#087E6D", "border-width": 3, width: 36, height: 36 } },
  { selector: "edge", style: { width: 1.5, "line-color": "#91A09A", "target-arrow-color": "#91A09A", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 9, color: "#5D6762" } },
] as unknown as NonNullable<ComponentProps<typeof CytoscapeComponent>["stylesheet"]>;

export function CytoscapeCanvas({ nodes, edges, onSelect }: { nodes: GraphNode[]; edges: GraphEdge[]; onSelect: (node: GraphNode) => void }) {
  const elements = [
    ...nodes.map((node) => ({ data: { id: nodeId(node), label: node.label, kind: node.kind } })),
    ...edges.map((edge, index) => ({ data: {
      id: edgeId(edge, index),
      source: edge.source_node_id ?? edge.source,
      target: edge.target_node_id ?? edge.target,
      label: edge.relation ?? edge.label ?? "related",
    } })),
  ];
  return <CytoscapeComponent
    elements={elements}
    layout={{ name: "cose", animate: false, padding: 36 }}
    stylesheet={graphStyles}
    style={{ height: "100%", width: "100%" }}
    cy={(cy) => cy.on("tap", "node", (event) => {
      const selected = nodes.find((node) => nodeId(node) === event.target.id());
      if (selected) onSelect(selected);
    })}
  />;
}
