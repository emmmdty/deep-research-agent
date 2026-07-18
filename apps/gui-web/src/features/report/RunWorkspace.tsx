import { useQuery } from "@tanstack/react-query";
import { BookOpen, GitCompareArrows, GitFork, ListChecks, Network, ScrollText } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { productApi } from "../../api/client";
import { AsyncState } from "../../components/AsyncState";
import type { Claim, EvidenceSpan, GraphNode } from "../../types";
import { EvidenceDrawer } from "../evidence/EvidenceDrawer";
import { EvidenceList } from "../evidence/EvidenceList";
import { RelationshipGraph } from "../graph/RelationshipGraph";
import { RunConnectionState, RunTelemetry, useRunEventStream } from "../runs/RunTelemetry";
import { ReportView } from "./ReportView";

type ViewId = "report" | "changes" | "evidence" | "graph" | "papers" | "runs";

const views = [
  { id: "report" as const, label: "报告", icon: ScrollText },
  { id: "changes" as const, label: "变化", icon: GitCompareArrows },
  { id: "evidence" as const, label: "证据", icon: ListChecks },
  { id: "graph" as const, label: "关系图", icon: GitFork },
  { id: "papers" as const, label: "论文", icon: BookOpen },
  { id: "runs" as const, label: "运行", icon: Network },
];

function nodeEvidenceIds(node: GraphNode): string[] {
  if (node.evidence_ids) return node.evidence_ids;
  const value = node.properties?.evidence_span_ids;
  return Array.isArray(value) ? value.map(String) : [];
}

export function RunWorkspace() {
  const { runId = "" } = useParams();
  const [view, setView] = useState<ViewId>("report");
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceSpan[]>([]);
  const connection = useRunEventStream(runId);
  const run = useQuery({ queryKey: ["run", runId], queryFn: () => productApi.getRun(runId), enabled: Boolean(runId) });
  const bundle = useQuery({ queryKey: ["bundle", runId], queryFn: () => productApi.getProductBundle(runId), enabled: run.data?.status === "completed" });
  const allClaims = useMemo(() => bundle.data ? [...bundle.data.accepted_claims, ...(bundle.data.qualified_claims ?? [])] : [], [bundle.data]);
  const allSpans = useMemo(() => allClaims.flatMap((claim) => claim.evidence_spans), [allClaims]);
  const graph = bundle.data?.research_graph ?? bundle.data?.claim_graph ?? { nodes: [], edges: [] };

  function selectClaim(claim: Claim) {
    setSelectedEvidence(claim.evidence_spans);
  }

  function selectNode(node: GraphNode) {
    const ids = new Set(nodeEvidenceIds(node));
    const selectedNodeId = node.node_id ?? node.id;
    for (const edge of graph.edges) {
      const sourceId = edge.source_node_id ?? edge.source;
      const targetId = edge.target_node_id ?? edge.target;
      if (sourceId === selectedNodeId || targetId === selectedNodeId) {
        for (const evidenceId of edge.evidence_span_ids ?? edge.evidence_ids ?? []) ids.add(evidenceId);
      }
    }
    const directClaim = allClaims.find((claim) => claim.claim_id === (node.node_id ?? node.id));
    const directSpans = directClaim?.evidence_spans ?? [];
    setSelectedEvidence([...directSpans, ...allSpans.filter((span) => ids.has(span.span_id) && !directSpans.some((direct) => direct.span_id === span.span_id))]);
  }

  return (
    <AsyncState loading={run.isPending || (run.data?.status === "completed" && bundle.isPending)} error={run.error ?? bundle.error}>
      {run.data && bundle.data ? (
        <div className={`report-workspace ${selectedEvidence.length ? "drawer-open" : ""}`}>
          <header className="report-toolbar">
            <div><span className="section-label">研究运行</span><strong>{run.data.question}</strong></div>
            <div className="run-summary"><RunConnectionState connection={connection} /><span className={`run-status ${run.data.status}`}>{run.data.status}</span><code>{run.data.run_id}</code><span>快照 {run.data.snapshot_cutoff ? new Date(run.data.snapshot_cutoff).toLocaleDateString("zh-CN") : "进行中"}</span></div>
          </header>
          <div className="view-tabs" role="tablist" aria-label="研究结果视图">
            {views.map(({ id, label, icon: Icon }) => <button aria-selected={view === id} key={id} onClick={() => setView(id)} role="tab" type="button"><Icon size={15} />{label}</button>)}
          </div>
          <div className="view-content">
            {view === "report" ? <ReportView bundle={bundle.data} onSelectClaim={selectClaim} /> : null}
            {view === "changes" ? <ChangesView audit={bundle.data.audit_summary} /> : null}
            {view === "evidence" ? <EvidenceList claims={allClaims} onSelect={selectClaim} /> : null}
            {view === "graph" ? <RelationshipGraph edges={graph.edges} nodes={graph.nodes} onSelect={selectNode} /> : null}
            {view === "papers" ? <PapersView bundle={bundle.data} /> : null}
            {view === "runs" ? <RunTelemetry bundle={bundle.data} run={run.data} /> : null}
          </div>
          {selectedEvidence.length ? <EvidenceDrawer onClose={() => setSelectedEvidence([])} spans={selectedEvidence} /> : null}
        </div>
      ) : run.data ? <PendingRun connection={connection} status={run.data.status} /> : null}
    </AsyncState>
  );
}

function PendingRun({ connection, status }: { connection: import("../runs/RunTelemetry").ConnectionState; status: string }) {
  return <div className="topic-overview"><RunConnectionState connection={connection} /><Network size={24} /><h2>Agent 集群正在执行</h2><p>当前状态：{status}。报告将在证据审计完成后显示。</p></div>;
}

function ChangesView({ audit }: { audit?: Record<string, unknown> }) {
  const entries = Object.entries(audit ?? {});
  return <div className="changes-view"><header><span className="section-label">当前运行</span><h2>当前审计摘要</h2><p className="view-caption">V1 仅展示本次冻结快照的审计结果，尚未计算跨快照差异。</p></header>{entries.length ? entries.map(([key, value]) => <div className="change-row" key={key}><code>{key}</code><span>{Array.isArray(value) ? value.join(", ") || "无" : JSON.stringify(value)}</span></div>) : <div className="view-empty">这份运行没有附带审计摘要。</div>}</div>;
}

function PapersView({ bundle }: { bundle: import("../../types").ReportBundle }) {
  const papers = bundle.papers ?? bundle.sources?.map((source) => ({
    document_id: String(source.metadata?.document_version_id ?? source.artifact_id ?? "source"),
    title: String(source.metadata?.title ?? source.title ?? source.uri ?? "来源文档"),
    year: Number(source.metadata?.year) || undefined,
    trust_tier: Number(source.metadata?.trust_tier) || undefined,
  })) ?? [];
  return <div className="paper-list">{papers.length ? papers.map((paper) => <article key={paper.document_id}><div className="paper-index">{String(papers.indexOf(paper) + 1).padStart(2, "0")}</div><div><h3>{paper.title}</h3><p><code>{paper.document_id}</code>{paper.year ? ` · ${paper.year}` : ""}{paper.trust_tier ? ` · 信任层级 ${paper.trust_tier}` : ""}</p></div></article>) : <div className="view-empty">Bundle 没有提供论文元数据。</div>}</div>;
}
