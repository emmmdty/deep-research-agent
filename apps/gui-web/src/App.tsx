import { FormEvent, useMemo, useState } from "react";

import { createApiClient, getDefaultApiBaseUrl, PublicJobEvent, PublicJobResponse, SubmitJobRequest } from "./api/client";

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

const sourceProfiles = [
  "company_trusted",
  "company_broad",
  "industry_trusted",
  "industry_broad",
  "public_then_private",
  "trusted_only",
];

const knownJobsKey = "dra.gui.knownJobs";

function readKnownJobs(): string[] {
  try {
    return JSON.parse(window.localStorage.getItem(knownJobsKey) || "[]") as string[];
  } catch {
    return [];
  }
}

function saveKnownJob(jobId: string): string[] {
  const next = Array.from(new Set([jobId, ...readKnownJobs()]));
  window.localStorage.setItem(knownJobsKey, JSON.stringify(next));
  return next;
}

export function App() {
  const apiBaseUrl = getDefaultApiBaseUrl();
  const api = useMemo(() => createApiClient({ baseUrl: apiBaseUrl }), [apiBaseUrl]);
  const [topic, setTopic] = useState("");
  const [sourceProfile, setSourceProfile] = useState("company_broad");
  const [manualJobId, setManualJobId] = useState("");
  const [knownJobs, setKnownJobs] = useState<string[]>(() => readKnownJobs());
  const [activeJob, setActiveJob] = useState<PublicJobResponse | null>(null);
  const [events, setEvents] = useState<PublicJobEvent[]>([]);
  const [bundle, setBundle] = useState<unknown>(null);
  const [message, setMessage] = useState("Ready for local API actions.");

  async function loadEvents(jobId: string) {
    const response = await api.getEvents(jobId, 0);
    setEvents(response.events);
  }

  async function submitJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Submitting local job...");
    const payload: SubmitJobRequest = {
      topic,
      max_loops: 1,
      research_profile: "default",
      source_profile: sourceProfile,
      allow_domains: [],
      deny_domains: [],
      connector_budget: null,
      start_worker: false,
    };
    const job = await api.submitJob(payload);
    setActiveJob(job);
    setKnownJobs(saveKnownJob(job.job_id));
    await loadEvents(job.job_id);
    setMessage(`Loaded ${job.job_id}`);
  }

  async function loadManualJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const jobId = manualJobId.trim();
    if (!jobId) {
      setMessage("Enter a job id first.");
      return;
    }
    setMessage(`Loading ${jobId}...`);
    const job = await api.getJob(jobId);
    setActiveJob(job);
    setKnownJobs(saveKnownJob(job.job_id));
    await loadEvents(job.job_id);
    setMessage(`Loaded ${job.job_id}`);
  }

  async function loadBundle() {
    if (!activeJob) {
      setMessage("Load a job before opening its bundle.");
      return;
    }
    setBundle(await api.getBundle(activeJob.job_id));
    setMessage(`Loaded bundle for ${activeJob.job_id}`);
  }

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

        <section className="workspace-grid" aria-label="Research job workspace">
          <form className="surface-card form-card" onSubmit={submitJob}>
            <span className="eyebrow">Submit</span>
            <h3>New local research job</h3>
            <label>
              Topic
              <textarea
                name="topic"
                onChange={(event) => setTopic(event.target.value)}
                placeholder="Anthropic company profile"
                required
                value={topic}
              />
            </label>
            <label>
              Source profile
              <select onChange={(event) => setSourceProfile(event.target.value)} value={sourceProfile}>
                {sourceProfiles.map((profile) => (
                  <option key={profile} value={profile}>
                    {profile}
                  </option>
                ))}
              </select>
            </label>
            <p className="helper-text">Phase 22 uses <code>start_worker=false</code> for bounded local submission.</p>
            <button type="submit">Submit local job</button>
          </form>

          <form className="surface-card form-card" onSubmit={loadManualJob}>
            <span className="eyebrow">Known Jobs</span>
            <h3>Load by job id</h3>
            <label>
              Manual job id
              <input
                onChange={(event) => setManualJobId(event.target.value)}
                placeholder="job-..."
                value={manualJobId}
              />
            </label>
            <button type="submit">Load job</button>
            <div className="known-jobs" aria-label="Known job ids">
              {knownJobs.length === 0 ? <p>No known jobs in this browser.</p> : null}
              {knownJobs.map((jobId) => (
                <code key={jobId}>{jobId}</code>
              ))}
            </div>
          </form>
        </section>

        <section className="surface-card job-detail" aria-label="Job detail">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Status</span>
              <h3>{activeJob ? activeJob.job_id : "No job loaded"}</h3>
            </div>
            <span className="status-pill">{message}</span>
          </div>

          {activeJob ? (
            <>
              <dl className="metric-grid">
                <div>
                  <dt>Status</dt>
                  <dd>{activeJob.status}</dd>
                </div>
                <div>
                  <dt>Audit gate</dt>
                  <dd>{activeJob.audit_gate_status}</dd>
                </div>
                <div>
                  <dt>Stage</dt>
                  <dd>{activeJob.current_stage}</dd>
                </div>
                <div>
                  <dt>Blocked critical claims</dt>
                  <dd>{activeJob.blocked_critical_claim_count}</dd>
                </div>
              </dl>

              <div className="artifact-actions">
                <button onClick={loadBundle} type="button">Load bundle</button>
                {activeJob.artifact_urls.report_html ? (
                  <a href={api.url(activeJob.artifact_urls.report_html)}>Open report HTML</a>
                ) : null}
              </div>

              <div className="split-panels">
                <article>
                  <h4>Events</h4>
                  {events.length === 0 ? <p>No events loaded yet.</p> : null}
                  {events.map((item) => (
                    <p key={item.event_id}>
                      <code>#{item.sequence}</code> {item.stage} / {item.event_type}: {item.message}
                    </p>
                  ))}
                </article>
                <article>
                  <h4>Bundle inspector</h4>
                  {bundle ? <pre>{JSON.stringify(bundle, null, 2)}</pre> : <p>Load a bundle to inspect claims and sources.</p>}
                </article>
              </div>
            </>
          ) : (
            <p>Submit a job or load a known job id to inspect status, events, and artifacts.</p>
          )}
        </section>
      </main>
    </div>
  );
}
