import { useEffect, useState } from "react";
import { ArrowRight, ShieldCheck, Gauge, FileCheck } from "lucide-react";
import type { Tab } from "../App";

interface HeadlineMetrics {
  metrics: Record<
    string,
    { value: number | string | null; sample_size?: number; reason?: string | null }
  >;
}

const headlineDescriptions: Record<string, string> = {
  completion_rate: "jobs reaching completed / submitted",
  bundle_emission_rate: "jobs emitting report_bundle.json / completed",
  critical_claim_support_precision: "supported critical claims / total critical claims",
  citation_error_rate: "claims whose evidence misses the frozen corpus / total claims",
  provenance_completeness: "claims with evidence span + snapshot / total claims",
  policy_compliance_rate: "claims grounded only in allowed sources / total claims",
  resume_success_rate: "resume attempts that complete successfully",
  stale_recovery_success_rate: "stale jobs recovered by the recovery worker",
};

export function HomePage({ navigate }: { navigate: (tab: Tab, runId?: string) => void }) {
  const [headline, setHeadline] = useState<HeadlineMetrics | null>(null);

  useEffect(() => {
    fetch("data/benchmarks/headline_metrics.json")
      .then((r) => r.json())
      .then(setHeadline)
      .catch(() => setHeadline(null));
  }, []);

  const metrics = headline?.metrics ?? {};

  return (
    <div className="home">
      <section className="hero">
        <h1>
          Evidence-first <span className="accent">multi-agent</span> deep research
        </h1>
        <p className="hero-sub">
          Deep research products answer. <strong>This system proves.</strong> A planner compiles a
          research brief into a task DAG; parallel <em>researcher</em> agents and a <em>critic</em>{" "}
          agent execute through governed model/tool gateways; every critical claim is audited
          against a frozen corpus before it reaches the report bundle.
        </p>
        <div className="hero-actions">
          <button className="btn-primary" onClick={() => navigate("reports", "dsv4-20260425")}>
            Explore a real report <ArrowRight size={15} />
          </button>
          <button className="btn-secondary" onClick={() => navigate("benchmark")}>
            See benchmark evidence
          </button>
          <button className="btn-secondary" onClick={() => navigate("trace", "dsv4-20260425")}>
            Replay agent trace
          </button>
        </div>
      </section>

      {Object.keys(metrics).length > 0 && (
        <section className="metric-strip">
          {Object.entries(metrics)
            .filter(([k]) => headlineDescriptions[k])
            .slice(0, 6)
            .map(([key, m]) => (
              <div className="metric-card" key={key}>
                <div className="metric-value">{String(m.value)}</div>
                <div className="metric-name">{key}</div>
                <div className="metric-desc">{headlineDescriptions[key]}</div>
              </div>
            ))}
        </section>
      )}

      <section className="pillars">
        <div className="pillar">
          <ShieldCheck size={26} className="pillar-icon" />
          <h3>Proven multi-agent value</h3>
          <p>
            Deterministic ablations show each mechanism matters: switch off the audit gate and
            unsupported-claim leakage jumps to 1.0; disable rerank and critical-claim support
            precision drops 1.0 → 0.5. Aligned with Anthropic's published +90.2% multi-agent
            finding — but measured locally, without API keys.
          </p>
        </div>
        <div className="pillar">
          <FileCheck size={26} className="pillar-icon" />
          <h3>Auditable report bundles</h3>
          <p>
            The deliverable is a machine-readable bundle: claims with typed evidence spans, a claim
            graph with support edges, conflict sets, audit decisions, and a human review queue.
            Unverifiable critical claims are <em>blocked</em>, not shipped.
          </p>
        </div>
        <div className="pillar">
          <Gauge size={26} className="pillar-icon" />
          <h3>Production-grade reliability</h3>
          <p>
            Checkpointed jobs survive cancel, retry, resume and stale recovery; leases, heartbeats
            and typed event journals are runtime contracts — the things agents fail at in
            production.
          </p>
        </div>
      </section>

      <section className="home-cases">
        <h2>Inspect real runs</h2>
        <div className="case-cards">
          {[
            {
              id: "dsv4-20260425",
              title: "DeepSeek-V4 架构科普",
              note: "audit gate blocked unsupported claims",
            },
            { id: "ths-20260522", title: "同花顺公司研究", note: "real retrieval + citations" },
            {
              id: "company-openai-surface",
              title: "OpenAI company profile",
              note: "deterministic eval fixture",
            },
          ].map((c) => (
            <button
              key={c.id}
              className="case-card"
              onClick={() => navigate("reports", c.id)}
            >
              <strong>{c.title}</strong>
              <span>{c.note}</span>
              <ArrowRight size={14} className="case-arrow" />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
