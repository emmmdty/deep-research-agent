import { getDefaultApiBaseUrl } from "./api/client";

type NavItem = {
  href: string;
  label: string;
  description: string;
};

const navItems: NavItem[] = [
  { href: "#/jobs", label: "Jobs", description: "Submit and inspect local research jobs." },
  { href: "#/artifacts", label: "Artifacts", description: "Open bundles, reports, claims, sources, and audit sidecars." },
  { href: "#/benchmarks", label: "Benchmarks", description: "Browse smoke_local and regression_local evidence." },
  { href: "#/docs", label: "Docs", description: "Reviewer-facing runbooks and GUI contract links." },
  { href: "#/settings", label: "Settings", description: "Local API base URL and desktop readiness." },
];

const capabilityCards = [
  {
    title: "Local API",
    eyebrow: "FastAPI",
    body: "Submit, status, event polling, bundle, artifact, review, and batch routes stay on the existing backend.",
  },
  {
    title: "Evidence Surface",
    eyebrow: "Bundles",
    body: "The GUI treats report_bundle.json as authoritative and keeps claims, sources, audits, and traces visible.",
  },
  {
    title: "Native Benchmarks",
    eyebrow: "Deterministic",
    body: "smoke_local remains the merge-safe gate while regression_local provides reviewer-facing suite coverage.",
  },
];

export function App() {
  const apiBaseUrl = getDefaultApiBaseUrl();

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-block">
          <span className="brand-kicker">Local Console</span>
          <h1>Deep Research Agent</h1>
          <p>Operator and reviewer workspace for jobs, bundles, audits, and native benchmark evidence.</p>
        </div>

        <nav className="nav-stack">
          {navItems.map((item) => (
            <a href={item.href} key={item.href}>
              <span>{item.label}</span>
              <small>{item.description}</small>
            </a>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <section className="hero-card">
          <div>
            <span className="eyebrow">Phase 21 Web Shell</span>
            <h2>Evidence-first operations, not a chat transcript.</h2>
            <p>
              This shell is wired for the local FastAPI boundary at <code>{apiBaseUrl}</code>. It keeps lifecycle
              status, audit gate status, artifacts, and benchmark surfaces as first-class areas.
            </p>
          </div>
          <div className="status-pill">READY_FOR_WEB_GUI</div>
        </section>

        <section className="card-grid" aria-label="Console capabilities">
          {capabilityCards.map((card) => (
            <article className="surface-card" key={card.title}>
              <span className="eyebrow">{card.eyebrow}</span>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
