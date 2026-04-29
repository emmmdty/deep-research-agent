import { FormEvent, useMemo, useState } from "react";

import { createApiClient, getDefaultApiBaseUrl, PublicJobEvent, PublicJobResponse, SubmitJobRequest } from "./api/client";

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
  const next = Array.from(new Set([jobId, ...readKnownJobs()])).slice(0, 12);
  window.localStorage.setItem(knownJobsKey, JSON.stringify(next));
  return next;
}

function statusLabel(job: PublicJobResponse | null): string {
  if (!job) {
    return "No job loaded";
  }
  return `${job.status} / ${job.current_stage}`;
}

export function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(getDefaultApiBaseUrl());
  const api = useMemo(() => createApiClient({ baseUrl: apiBaseUrl }), [apiBaseUrl]);
  const [topic, setTopic] = useState("");
  const [sourceProfile, setSourceProfile] = useState("company_broad");
  const [maxLoops, setMaxLoops] = useState(3);
  const [startWorker, setStartWorker] = useState(false);
  const [manualJobId, setManualJobId] = useState("");
  const [knownJobs, setKnownJobs] = useState<string[]>(() => readKnownJobs());
  const [activeJob, setActiveJob] = useState<PublicJobResponse | null>(null);
  const [events, setEvents] = useState<PublicJobEvent[]>([]);
  const [bundle, setBundle] = useState<unknown>(null);
  const [message, setMessage] = useState("Ready");

  async function runAction(action: () => Promise<void>) {
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    }
  }

  async function loadEvents(jobId: string) {
    const response = await api.getEvents(jobId, 0);
    setEvents(response.events);
  }

  async function loadJob(jobId: string) {
    const job = await api.getJob(jobId);
    setActiveJob(job);
    setKnownJobs(saveKnownJob(job.job_id));
    await loadEvents(job.job_id);
    setBundle(null);
    setMessage(`Loaded ${job.job_id}`);
  }

  function submitJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runAction(async () => {
      setMessage("Submitting job");
      const payload: SubmitJobRequest = {
        topic,
        max_loops: maxLoops,
        research_profile: "default",
        source_profile: sourceProfile,
        allow_domains: [],
        deny_domains: [],
        connector_budget: null,
        start_worker: startWorker,
      };
      const job = await api.submitJob(payload);
      setActiveJob(job);
      setKnownJobs(saveKnownJob(job.job_id));
      await loadEvents(job.job_id);
      setBundle(null);
      setMessage(`Created ${job.job_id}`);
    });
  }

  function loadManualJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const jobId = manualJobId.trim();
    if (!jobId) {
      setMessage("Enter a job id");
      return;
    }
    void runAction(() => loadJob(jobId));
  }

  function refreshActiveJob() {
    if (!activeJob) {
      setMessage("Load a job first");
      return;
    }
    void runAction(() => loadJob(activeJob.job_id));
  }

  function loadBundle() {
    if (!activeJob) {
      setMessage("Load a job first");
      return;
    }
    void runAction(async () => {
      setBundle(await api.getBundle(activeJob.job_id));
      setMessage(`Loaded bundle for ${activeJob.job_id}`);
    });
  }

  const artifactEntries = activeJob ? Object.entries(activeJob.artifact_urls) : [];

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Workspace navigation">
        <div className="brand-block">
          <span className="brand-kicker">Deep Research Agent</span>
          <strong>{statusLabel(activeJob)}</strong>
        </div>
        <nav className="nav-stack">
          <a href="#submit">Submit</a>
          <a href="#status">Status</a>
          <a href="#artifacts">Artifacts</a>
          <a href="#settings">Settings</a>
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <h1>Research Workbench</h1>
            <p>Submit local research jobs, monitor progress, and open generated artifacts.</p>
          </div>
          <span className="status-pill">{message}</span>
        </header>

        <section className="panel settings-panel" id="settings" aria-label="API settings">
          <label>
            API base URL
            <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
          </label>
          <a className="text-link" href={`${apiBaseUrl.replace(/\/+$/, "")}/docs`}>
            Open API docs
          </a>
        </section>

        <section className="workspace-grid">
          <form className="panel form-panel" id="submit" onSubmit={submitJob}>
            <div className="section-heading">
              <h2>New Job</h2>
              <button type="submit">Submit</button>
            </div>
            <label>
              Topic
              <textarea
                name="topic"
                onChange={(event) => setTopic(event.target.value)}
                placeholder="OpenAI company profile"
                required
                value={topic}
              />
            </label>
            <div className="form-row">
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
              <label>
                Max loops
                <input
                  min="1"
                  max="8"
                  onChange={(event) => setMaxLoops(Number(event.target.value))}
                  type="number"
                  value={maxLoops}
                />
              </label>
            </div>
            <label className="checkbox-row">
              <input checked={startWorker} onChange={(event) => setStartWorker(event.target.checked)} type="checkbox" />
              Start worker immediately
            </label>
          </form>

          <form className="panel form-panel" onSubmit={loadManualJob}>
            <div className="section-heading">
              <h2>Open Job</h2>
              <button type="submit">Load</button>
            </div>
            <label>
              Job id
              <input
                onChange={(event) => setManualJobId(event.target.value)}
                placeholder="20260429T000000Z-abc12345"
                value={manualJobId}
              />
            </label>
            <div className="known-jobs" aria-label="Known job ids">
              {knownJobs.length === 0 ? <p>No saved jobs in this browser.</p> : null}
              {knownJobs.map((jobId) => (
                <button key={jobId} onClick={() => void runAction(() => loadJob(jobId))} type="button">
                  {jobId}
                </button>
              ))}
            </div>
          </form>
        </section>

        <section className="panel job-panel" id="status" aria-label="Job status">
          <div className="section-heading">
            <div>
              <h2>{activeJob ? activeJob.job_id : "Job Status"}</h2>
              <p>{activeJob ? activeJob.topic : "Submit or load a job to inspect runtime state."}</p>
            </div>
            <button onClick={refreshActiveJob} type="button">
              Refresh
            </button>
          </div>

          <dl className="metric-grid">
            <div>
              <dt>Status</dt>
              <dd>{activeJob?.status ?? "-"}</dd>
            </div>
            <div>
              <dt>Stage</dt>
              <dd>{activeJob?.current_stage ?? "-"}</dd>
            </div>
            <div>
              <dt>Audit</dt>
              <dd>{activeJob?.audit_gate_status ?? "-"}</dd>
            </div>
            <div>
              <dt>Blocked Claims</dt>
              <dd>{activeJob?.blocked_critical_claim_count ?? "-"}</dd>
            </div>
          </dl>

          <div className="split-panels">
            <article>
              <h3>Events</h3>
              {events.length === 0 ? <p>No events loaded.</p> : null}
              {events.map((item) => (
                <p key={item.event_id}>
                  <code>#{item.sequence}</code> {item.stage} / {item.event_type}: {item.message}
                </p>
              ))}
            </article>
            <article id="artifacts">
              <div className="section-heading compact">
                <h3>Artifacts</h3>
                <button onClick={loadBundle} type="button">
                  Load Bundle
                </button>
              </div>
              {artifactEntries.length === 0 ? <p>No artifact links are available yet.</p> : null}
              <div className="artifact-list">
                {artifactEntries.map(([name, href]) => (
                  <a href={api.url(href)} key={name}>
                    {name}
                  </a>
                ))}
              </div>
            </article>
          </div>

          <article className="bundle-viewer">
            <h3>Bundle Inspector</h3>
            {bundle ? <pre>{JSON.stringify(bundle, null, 2)}</pre> : <p>Load a bundle to inspect claims and sources.</p>}
          </article>
        </section>
      </main>
    </div>
  );
}
