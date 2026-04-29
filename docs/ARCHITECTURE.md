# Architecture

The product runtime lives under `src/deep_research_agent/`.

```text
gateway/         CLI, FastAPI app, batch loading, artifact access
research_jobs/   job records, checkpoints, worker orchestration, SQLite store
runtime/         planning, collection, verification, claim audit input, writing
connectors/      web, GitHub, arXiv, file ingestion, snapshots
policy/          source profiles, budgets, source filtering
auditor/         claim graph, review queue, audit decision helpers
reporting/       artifact schema validation and report bundle emission
providers/       OpenAI, Anthropic, and compatible provider routing
config/          environment-backed settings
```

Jobs are created through the CLI or API, persisted in SQLite, and advanced by the worker. Each stage writes events and checkpoint state so a job can be inspected, cancelled, retried, resumed, or refined.

Runtime artifacts are filesystem-first. The API and CLI read from the same job directories, so the Web UI can open reports, bundles, sources, claims, and audit sidecars without a separate storage service.
