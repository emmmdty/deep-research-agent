import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ShieldAlert, ShieldCheck, CheckCircle2, XCircle, MinusCircle } from "lucide-react";
import { RUN_CASES, useBundle } from "../data";
import type { ClaimRecord, EvidenceFragment, SourceRecord, SupportEdge } from "../data/types";

export function ReportBrowser({
  selectedRun,
  onSelectRun,
}: {
  selectedRun: string;
  onSelectRun: (id: string) => void;
}) {
  const active = RUN_CASES.find((c) => c.id === selectedRun) ?? RUN_CASES[0];
  const bundle = useBundle(active.bundlePath);
  const [activeTab, setActiveTab] = useState<"report" | "claims" | "sources" | "audit">("report");
  const [showMarkdown, setShowMarkdown] = useState(false);

  const evidenceById = useMemo(() => {
    const map = new Map<string, EvidenceFragment>();
    for (const e of bundle?.evidence_fragments ?? []) map.set(e.evidence_id, e);
    return map;
  }, [bundle]);

  const sourceById = useMemo(() => {
    const map = new Map<string, SourceRecord>();
    for (const s of bundle?.sources ?? []) map.set(s.source_id, s);
    return map;
  }, [bundle]);

  const edgesByClaim = useMemo(() => {
    const map = new Map<string, SupportEdge[]>();
    for (const e of bundle?.claim_support_edges ?? []) {
      const list = map.get(e.claim_id) ?? [];
      list.push(e);
      map.set(e.claim_id, list);
    }
    return map;
  }, [bundle]);

  const supported = bundle?.claims.filter((c) => c.status === "supported").length ?? 0;
  const unsupported = bundle?.claims.filter((c) => c.status === "unsupported").length ?? 0;
  const gate = bundle?.audit_summary.gate_status;

  if (!bundle) {
    return (
      <div className="page">
        <h2>Report Bundles</h2>
        <RunSelector selectedRun={selectedRun} onSelectRun={onSelectRun} />
        <p className="muted">Loading bundle…</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h2>Report Bundles</h2>
      <RunSelector selectedRun={selectedRun} onSelectRun={onSelectRun} />

      <div className="run-meta">
        <span className="tag tag-real">{active.tag}</span>
        <code>{bundle.job.job_id}</code>
        <span className="muted">source profile: {bundle.job.source_profile}</span>
        <span className="muted">runtime: {bundle.job.runtime_path ?? "n/a"}</span>
        <span
          className={`gate-pill ${gate === "passed" ? "ok" : gate === "blocked" ? "blocked" : "warn"}`}
        >
          audit gate: {gate ?? "n/a"}
        </span>
      </div>

      <p className="run-desc">{active.description}</p>

      <div className="tabs">
        <button
          className={`tab-btn${activeTab === "report" ? " active" : ""}`}
          onClick={() => setActiveTab("report")}
        >
          Report ({bundle.claims.length} claims)
        </button>
        <button
          className={`tab-btn${activeTab === "claims" ? " active" : ""}`}
          onClick={() => setActiveTab("claims")}
        >
          Claims &amp; evidence
        </button>
        <button
          className={`tab-btn${activeTab === "sources" ? " active" : ""}`}
          onClick={() => setActiveTab("sources")}
        >
          Sources ({bundle.sources.length})
        </button>
        <button
          className={`tab-btn${activeTab === "audit" ? " active" : ""}`}
          onClick={() => setActiveTab("audit")}
        >
          Audit summary
        </button>
      </div>

      {activeTab === "report" && (
        <div className="report-view">
          <div className="report-actions">
            <button className="btn-small" onClick={() => setShowMarkdown(!showMarkdown)}>
              {showMarkdown ? "Show rendered" : "Show markdown"}
            </button>
            <span className="muted">supported {supported} / unsupported {unsupported}</span>
          </div>
          {showMarkdown ? (
            <pre className="markdown-raw">{bundle.report_text}</pre>
          ) : (
            <div className="report-rendered">
              <ReactMarkdown>{bundle.report_text}</ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {activeTab === "claims" && (
        <div className="claims-table">
          {bundle.claims.map((claim) => (
            <ClaimRow
              key={claim.claim_id}
              claim={claim}
              edges={edgesByClaim.get(claim.claim_id) ?? []}
              evidence={evidenceById}
              sources={sourceById}
            />
          ))}
        </div>
      )}

      {activeTab === "sources" && (
        <div className="sources-table">
          {bundle.sources.map((s) => (
            <div className="source-row" key={s.source_id}>
              <div className="source-title">
                <strong>{s.title || s.canonical_uri}</strong>
                <span className="muted">{s.source_type}</span>
              </div>
              {s.canonical_uri && (
                <a className="source-url" href={s.canonical_uri} target="_blank" rel="noreferrer">
                  {s.canonical_uri}
                </a>
              )}
              {s.snippet && <p className="muted">{s.snippet}</p>}
            </div>
          ))}
        </div>
      )}

      {activeTab === "audit" && (
        <div className="audit-view">
          <AuditSummary bundle={{
            status: bundle.audit_summary.status,
            gate_status: bundle.audit_summary.gate_status ?? "n/a",
            event_count: bundle.audit_summary.event_count,
            stages: bundle.audit_summary.stages,
          }} />
          <h3>Audit events</h3>
          <pre className="audit-events">
            {JSON.stringify(bundle.audit_events ?? [], null, 1)}
          </pre>
        </div>
      )}
    </div>
  );
}

function RunSelector({ selectedRun, onSelectRun }: { selectedRun: string; onSelectRun: (id: string) => void }) {
  return (
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
  );
}

function ClaimRow({
  claim,
  edges,
  evidence,
  sources,
}: {
  claim: ClaimRecord;
  edges: SupportEdge[];
  evidence: Map<string, EvidenceFragment>;
  sources: Map<string, SourceRecord>;
}) {
  const statusIcon =
    claim.status === "supported" ? (
      <CheckCircle2 size={16} className="ok" />
    ) : claim.status === "unsupported" ? (
      <XCircle size={16} className="bad" />
    ) : (
      <MinusCircle size={16} className="warn" />
    );
  return (
    <div className="claim-row">
      <div className="claim-head">
        <span className={`criticality ${claim.criticality}`}>{claim.criticality}</span>
        {statusIcon}
        <code>{claim.claim_id}</code>
        <span className="muted">{claim.section_ref}</span>
      </div>
      <p className="claim-text">{claim.text}</p>
      {edges.length > 0 ? (
        <div className="edge-list">
          {edges.map((edge) => {
            const frag = evidence.get(edge.evidence_id ?? "");
            const src = sources.get(edge.source_id ?? "");
            return (
              <div className="edge" key={edge.edge_id}>
                <span className={`relation ${edge.relation}`}>{edge.relation}</span>
                <span className="confidence">{edge.confidence}</span>
                <blockquote className="edge-excerpt">{(frag?.excerpt ?? "").slice(0, 220)}</blockquote>
                <span className="muted">
                  ← {src?.title?.slice(0, 60) ?? edge.source_id}
                  {edge.grounding_status ? ` · ${edge.grounding_status}` : ""}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="muted">no support edge — routed to review queue</p>
      )}
    </div>
  );
}

function AuditSummary({ bundle }: { bundle: { status: string; gate_status: string; event_count?: number; stages?: string[] } }) {
  const icon =
    bundle.gate_status === "passed" ? (
      <ShieldCheck size={40} className="ok" />
    ) : (
      <ShieldAlert size={40} className="bad" />
    );
  return (
    <div className="audit-summary">
      {icon}
      <div>
        <h3>
          Gate status: <span className={bundle.gate_status}>{bundle.gate_status}</span>
        </h3>
        <p className="muted">
          status={bundle.status} · {bundle.event_count ?? 0} audit events ·{" "}
          {(bundle.stages ?? []).length} stage transitions
        </p>
      </div>
    </div>
  );
}
