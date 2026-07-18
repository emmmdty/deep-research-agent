import { lazy, Suspense } from "react";

import type { GraphEdge, GraphNode } from "../../types";

const nodeId = (node: GraphNode) => node.node_id ?? node.id ?? node.label;
const CytoscapeCanvas = lazy(() => import("./CytoscapeCanvas").then((module) => ({ default: module.CytoscapeCanvas })));

export function RelationshipGraph({ nodes, edges, onSelect }: { nodes: GraphNode[]; edges: GraphEdge[]; onSelect: (node: GraphNode) => void }) {
  const isJsdom = navigator.userAgent.toLowerCase().includes("jsdom");

  return (
    <div className="graph-workspace">
      <div className="graph-canvas" aria-label="研究关系图">
        {!isJsdom && nodes.length ? (
          <Suspense fallback={<div className="graph-placeholder">正在载入关系图...</div>}><CytoscapeCanvas edges={edges} nodes={nodes} onSelect={onSelect} /></Suspense>
        ) : <div className="graph-placeholder">{nodes.length ? "关系图预览" : "暂无关系节点"}</div>}
      </div>
      <div className="graph-node-list" aria-label="图节点">
        {nodes.map((node) => <button aria-label={node.label} key={nodeId(node)} onClick={() => onSelect(node)} type="button"><i data-kind={node.kind} />{node.label}<small>{node.kind}</small></button>)}
      </div>
    </div>
  );
}
