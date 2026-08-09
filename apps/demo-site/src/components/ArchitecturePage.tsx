const LAYERS = [
  {
    layer: "Agent orchestration",
    modules: ["orchestration/dag.py", "orchestration/scheduler.py", "orchestration/workers.py", "orchestration/reducer.py"],
    role: "ResearchPlanner compiles a brief into an immutable task DAG; a bounded asyncio scheduler runs ready tasks in parallel (≤8 workers) with typed TaskSpec/WorkerOutput message passing; workers may fan out new tasks; a critic task audits all research outputs.",
  },
  {
    layer: "Agent roles",
    modules: ["orchestration/dag.py (researcher tasks)", "critic tasks → CriticDecision"],
    role: "One researcher task per objective (parallel); critic dependencies emit accepted / qualified / contradicted / unresolved decisions.",
  },
  {
    layer: "Governance",
    modules: ["tool_gateway/gateway.py", "model_runtime/registry.py", "policy/"],
    role: "Role allow-lists, tenant checks, idempotency, caching, budget caps, timeout/retry; per-role model fallback chains with AES-GCM encrypted credentials.",
  },
  {
    layer: "Evidence & audit",
    modules: ["auditor/semantic.py", "evidence_store/", "corpus/"],
    role: "Claim graph with support edges, conflict sets and review queues; frozen corpus manifests with content hashes; provenance snapshots.",
  },
  {
    layer: "Deliverable",
    modules: ["reporting/bundle_v2.py"],
    role: "Deterministic reduction → audit → report_bundle.json (+ report.md/html) with sidecar artifacts (claims, sources, audit decision, review queue, claim graph, trace).",
  },
  {
    layer: "Reliability",
    modules: ["research_jobs/", "observability/"],
    role: "Checkpoints, event journals, leases, heartbeats, resume/retry/refine/cancel; credential-safe OpenTelemetry spans exported to Phoenix.",
  },
  {
    layer: "Product surface",
    modules: ["gateway/cli.py", "gateway/api.py", "product/", "apps/gui-web/"],
    role: "CLI, local HTTP API with SSE event streams, PostgreSQL-backed multi-tenant product API, React workspace UI.",
  },
];

const LIFE_CYCLE = [
  ["user topic", "intent routing (direct / clarify / refresh)"],
  ["ResearchPlanner.plan()", "brief → ResearchDAG"],
  ["ResearchScheduler.run()", "bounded asyncio, ≤8 workers, typed messages"],
  ["ToolGateway / ModelRegistry", "governed retrieval, role model chains"],
  ["EvidenceReducer.reduce()", "dedupe + merge evidence"],
  ["EvidenceAuditor.audit()", "claim graph, support edges, gate decision"],
  ["ReportBundleCompilerV2.compile()", "report_bundle.json + report.md/html"],
  ["job artifacts", "workspace/research_jobs/<job_id>/"],
];

export function ArchitecturePage() {
  return (
    <div className="page">
      <h2>Architecture</h2>
      <p className="page-note">
        Two runtime generations exist: the V2 product path (<code>scheduler-v2</code>, the story
        below) and an archived graph-first path (<code>orchestrator-v1</code>) kept for
        compatibility. Everything on this page is <code>src/deep_research_agent/</code>.
      </p>

      <section className="bench-section">
        <h3>Execution pipeline</h3>
        <div className="pipeline">
          {LIFE_CYCLE.map(([name, desc], i) => (
            <div className="pipeline-step" key={name}>
              <div className="step-index">{i + 1}</div>
              <code>{name}</code>
              <span className="muted">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>Runtime layers</h3>
        <div className="layer-list">
          {LAYERS.map((l) => (
            <div className="layer-card" key={l.layer}>
              <h4>{l.layer}</h4>
              <div className="layer-modules">
                {l.modules.map((m) => (
                  <code key={m}>{m}</code>
                ))}
              </div>
              <p className="muted">{l.role}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>Reliability contracts</h3>
        <ul className="contract-list">
          <li>
            <strong>Checkpoints &amp; events</strong> — every job writes a typed event journal
            (<code>trace.jsonl</code>) and can resume from the latest checkpoint.
          </li>
          <li>
            <strong>Leases &amp; heartbeats</strong> — workers hold leased jobs; stale jobs are
            recovered by the recovery worker (deterministic <code>stale_recovery</code> suites
            cover this).
          </li>
          <li>
            <strong>Fail-closed production mode</strong> — production requires an explicit{" "}
            <code>SCHEDULER_FACTORY_PATH</code>; the runtime never silently degrades to the offline
            demo.
          </li>
          <li>
            <strong>Credential-safe observability</strong> — OTel spans redact secrets before
            export.
          </li>
        </ul>
      </section>

      <section className="bench-section">
        <h3>User-facing architecture</h3>
        <img
          src="assets/architecture-overview.png"
          alt="Deep Research Agent architecture overview"
          className="arch-img"
        />
      </section>
    </div>
  );
}
