import { useEffect, useState } from "react";
import { COMPETITORS, INDUSTRY_PAIN_POINTS } from "../data/competitors";
import { loadJson } from "../data";

interface HeadlineMetrics {
  metrics: Record<string, { value: number | string | null; sample_size?: number; reason?: string | null }>;
}

interface AblationSummary {
  source: string;
  ablations: Array<{
    id: string;
    name: string;
    scope: string;
    key_delta: string;
    interpretation: string;
  }>;
}

interface ReleaseManifest {
  status?: string;
  suites?: Array<Record<string, unknown>>;
  passed_suites?: number;
  total_suites?: number;
}

export function BenchmarkPage() {
  const [headline, setHeadline] = useState<HeadlineMetrics | null>(null);
  const [ablation, setAblation] = useState<AblationSummary | null>(null);
  const [release, setRelease] = useState<ReleaseManifest | null>(null);
  const [portfolio, setPortfolio] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    loadJson<HeadlineMetrics>("data/benchmarks/headline_metrics.json")
      .then(setHeadline)
      .catch(() => setHeadline(null));
    loadJson<AblationSummary>("data/benchmarks/ablation_summary.json")
      .then(setAblation)
      .catch(() => setAblation(null));
    loadJson<ReleaseManifest>("data/benchmarks/release_manifest.json")
      .then(setRelease)
      .catch(() => setRelease(null));
    loadJson<Record<string, unknown>>("data/benchmarks/portfolio_summary.json")
      .then(setPortfolio)
      .catch(() => setPortfolio(null));
  }, []);

  const metrics = headline?.metrics ?? {};

  return (
    <div className="page">
      <h2>Benchmark Evidence</h2>
      <p className="page-note">
        All committed numbers are deterministic and reproducible locally — no API keys, no
        network. Commands to reproduce every table below are in{" "}
        <code>docs/benchmarks/COMPARISON_PROTOCOL.md</code>.
      </p>

      <section className="bench-section">
        <h3>1 · Release gate (deterministic smoke)</h3>
        <div className="gate-card">
          <span className={`gate-pill ${release?.status === "passed" ? "ok" : "warn"}`}>
            {release?.status ?? "…"}
          </span>
          <span className="muted">
            {release?.suites?.length ?? 0} suites · authoritative merge-safe gate:
            <code> evals/reports/phase5_local_smoke/</code>
          </span>
        </div>
        <div className="metric-grid">
          {Object.entries(metrics)
            .filter(([k]) => k !== "ttff_seconds_p50" && k !== "ttfr_seconds_p50")
            .map(([key, m]) => (
              <div className="metric-cell" key={key}>
                <strong>{String(m.value)}</strong>
                <span>{key}</span>
                <span className="muted">n={m.sample_size ?? "—"}</span>
              </div>
            ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>2 · Ablations — why the multi-agent machinery exists</h3>
        <p className="page-note">
          Switching off a single mechanism and observing a measurable regression is the strongest
          evidence that the mechanism contributes. Source:{" "}
          <code>{ablation?.source ?? "ablation_summary.md"}</code>
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>Mechanism</th>
              <th>Delta when removed</th>
              <th>Interpretation</th>
            </tr>
          </thead>
          <tbody>
            {(ablation?.ablations ?? [])
              .filter((a) => a.id !== "provider_auto_vs_manual" && a.id !== "new_runtime_vs_legacy")
              .map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.name}</strong>
                    <div className="muted">{a.scope}</div>
                  </td>
                  <td>
                    <code>{a.key_delta}</code>
                  </td>
                  <td>{a.interpretation}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </section>

      <section className="bench-section">
        <h3>3 · External benchmark portfolio</h3>
        <p className="page-note">
          Adapters with integrity guards (material denylists, canary detection) for BrowseComp,
          GAIA, LongBench-v2, LongFact and Facts Grounding. Challenge-track only — they never
          upgrade into the authoritative release gate.
        </p>
        {portfolio && (
          <pre className="audit-events">
            {JSON.stringify(portfolio.runs ?? portfolio, null, 1).slice(0, 2600)}
          </pre>
        )}
      </section>

      <section className="bench-section">
        <h3>4 · Industry comparison</h3>
        <p className="page-note">
          Public figures with sources; full citations in{" "}
          <code>docs/final/COMPETITIVE_LANDSCAPE.md</code>. Honest caveat: our committed numbers
          are deterministic local gates, not live-provider head-to-heads — that is an explicit
          roadmap item.
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Form</th>
              <th>Open source</th>
              <th>Audit trail</th>
              <th>Benchmark signal</th>
              <th>Cost posture</th>
            </tr>
          </thead>
          <tbody>
            {COMPETITORS.map((c) => (
              <tr key={c.product} className={c.product === "This project" ? "highlight-row" : ""}>
                <td>
                  <strong>{c.product}</strong>
                  <div className="muted">{c.reference}</div>
                </td>
                <td>{c.form}</td>
                <td>{c.openSource}</td>
                <td>{c.auditTrail}</td>
                <td>{c.benchmark}</td>
                <td>{c.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bench-section">
        <h3>5 · Industry evidence for multi-agent research</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Finding</th>
              <th>What we do about it</th>
            </tr>
          </thead>
          <tbody>
            {INDUSTRY_PAIN_POINTS.map((p, i) => (
              <tr key={i}>
                <td className="muted">{p.source}</td>
                <td>{p.finding}</td>
                <td>{p.implication}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
