import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { CheckCircle2, XCircle, MinusCircle, ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";
import type {
  ClaimRecord,
  EvidenceFragment,
  ReportBundle,
  SourceRecord,
  SupportEdge,
} from "../data/types";

export type ReportTab = "report" | "claims" | "sources" | "audit";

const STATUS_LABEL: Record<string, string> = {
  supported: "有证据支持",
  unsupported: "无证据（拦截）",
  qualified: "有条件支持",
  unverifiable: "无法验证",
  partially_supported: "部分支持",
};

const CRITICALITY_LABEL: Record<string, string> = {
  high: "关键",
  medium: "重要",
  low: "一般",
};

export function ReportViewer({
  bundle,
  notice,
  activeTab,
  onTab,
}: {
  bundle: ReportBundle;
  notice?: React.ReactNode;
  activeTab: ReportTab;
  onTab: (tab: ReportTab) => void;
}) {
  const [showMarkdown, setShowMarkdown] = useState(false);

  const evidenceById = useMemo(() => {
    const map = new Map<string, EvidenceFragment>();
    for (const e of bundle.evidence_fragments ?? []) map.set(e.evidence_id, e);
    return map;
  }, [bundle]);

  const sourceById = useMemo(() => {
    const map = new Map<string, SourceRecord>();
    for (const s of bundle.sources ?? []) map.set(s.source_id, s);
    return map;
  }, [bundle]);

  const edgesByClaim = useMemo(() => {
    const map = new Map<string, SupportEdge[]>();
    for (const e of bundle.claim_support_edges ?? []) {
      const list = map.get(e.claim_id) ?? [];
      list.push(e);
      map.set(e.claim_id, list);
    }
    return map;
  }, [bundle]);

  const supported = bundle.claims.filter((c) => c.status === "supported").length;
  const unsupported = bundle.claims.filter((c) => c.status === "unsupported" || c.status === "unverifiable").length;
  const qualified = bundle.claims.filter((c) => c.status === "qualified" || c.status === "partially_supported").length;
  const gate = bundle.audit_summary?.gate_status;

  return (
    <div className="report-viewer">
      {notice && <div className="notice-bar">{notice}</div>}
      <div className="report-stats">
        <span className="stat">
          结论 <strong>{bundle.claims.length}</strong>
        </span>
        <span className="stat ok">
          有证据 <strong>{supported}</strong>
        </span>
        {qualified > 0 && (
          <span className="stat warn">
            有条件 <strong>{qualified}</strong>
          </span>
        )}
        {unsupported > 0 && (
          <span className="stat bad">
            被拦截 <strong>{unsupported}</strong>
          </span>
        )}
        <span className="stat">
          来源 <strong>{bundle.sources.length}</strong>
        </span>
        <span
          className={`gate-pill ${gate === "passed" ? "ok" : gate === "blocked" ? "blocked" : "warn"}`}
        >
          审计门禁：{gate === "passed" ? "通过" : gate === "blocked" ? "拦截（需人工复核）" : gate ?? "未知"}
        </span>
      </div>

      <div className="tabs">
        <button className={`tab-btn${activeTab === "report" ? " active" : ""}`} onClick={() => onTab("report")}>
          研究报告
        </button>
        <button className={`tab-btn${activeTab === "claims" ? " active" : ""}`} onClick={() => onTab("claims")}>
          结论与证据（{bundle.claims.length}）
        </button>
        <button className={`tab-btn${activeTab === "sources" ? " active" : ""}`} onClick={() => onTab("sources")}>
          引用来源（{bundle.sources.length}）
        </button>
        <button className={`tab-btn${activeTab === "audit" ? " active" : ""}`} onClick={() => onTab("audit")}>
          审计记录
        </button>
      </div>

      {activeTab === "report" && (
        <div className="report-view">
          <div className="report-actions">
            <button className="btn-small" onClick={() => setShowMarkdown(!showMarkdown)}>
              {showMarkdown ? "查看渲染效果" : "查看原始 markdown"}
            </button>
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
                <span className="muted">{s.source_type === "web" ? "网页" : s.source_type}</span>
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
          <AuditSummary bundle={bundle} />
          {(bundle.conflict_sets ?? []).length > 0 && (
            <div className="conflicts">
              <h4>
                <AlertTriangle size={15} /> 检测到的矛盾点
              </h4>
              {bundle.conflict_sets!.map((c) => (
                <div className="conflict" key={c.conflict_id ?? Math.random()}>
                  {c.description}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
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
  const [expanded, setExpanded] = useState(false);
  const statusIcon =
    claim.status === "supported" ? (
      <CheckCircle2 size={16} className="ok" />
    ) : claim.status === "unsupported" || claim.status === "unverifiable" ? (
      <XCircle size={16} className="bad" />
    ) : (
      <MinusCircle size={16} className="warn" />
    );
  return (
    <div className={`claim-row ${claim.status}`}>
      <div className="claim-head">
        <span className={`criticality ${claim.criticality}`}>
          {CRITICALITY_LABEL[claim.criticality] ?? claim.criticality}
        </span>
        {statusIcon}
        <span className={`claim-status ${claim.status}`}>
          {STATUS_LABEL[claim.status] ?? claim.status}
        </span>
        <span className="muted">{claim.section_ref}</span>
        {edges.length > 0 && (
          <button className="btn-small" onClick={() => setExpanded(!expanded)}>
            {expanded ? "收起证据" : `查看证据（${edges.length}）`}
          </button>
        )}
      </div>
      <p className="claim-text">{claim.text}</p>
      {expanded && edges.length > 0 && (
        <div className="edge-list">
          {edges.map((edge) => {
            const frag = evidence.get(edge.evidence_id ?? "");
            const src = sources.get(edge.source_id ?? "");
            const relLabel =
              edge.relation === "supported" ? "支持" : edge.relation === "context_only" ? "仅有背景" : edge.relation;
            return (
              <div className="edge" key={edge.edge_id}>
                <span className={`relation ${edge.relation}`}>
                  {relLabel} · 置信度 {(edge.confidence ?? 0).toFixed(2)}
                </span>
                <blockquote className="edge-excerpt">"{(frag?.excerpt ?? "").slice(0, 260)}"</blockquote>
                <span className="muted">
                  ← {(src?.title ?? edge.source_id ?? "").slice(0, 70)}
                  {src?.canonical_uri ? ` · ${src.canonical_uri.slice(0, 50)}` : ""}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {edges.length === 0 && (
        <p className="muted">该结论没有可用证据——已进入人工复核队列，不会出现在正式报告结论中。</p>
      )}
    </div>
  );
}

function AuditSummary({ bundle }: { bundle: ReportBundle }) {
  const gate = bundle.audit_summary?.gate_status;
  const icon =
    gate === "passed" ? <ShieldCheck size={36} className="ok" /> : <ShieldAlert size={36} className="bad" />;
  return (
    <div className="audit-summary">
      {icon}
      <div>
        <h3>
          审计门禁：<span className={gate}>{gate === "passed" ? "通过" : "拦截"}</span>
        </h3>
        <p className="muted">
          系统将每条结论与冻结证据库中的证据片段逐条比对（claim graph + 支持边），无法验证的关键结论
          进入人工复核队列。下方为本次运行的审计事件记录。
        </p>
      </div>
    </div>
  );
}
