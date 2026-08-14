# Repository Map

This map is for first-time GitHub reviewers. The main implementation is not root-package-first:
the canonical runtime lives under `src/deep_research_agent/`.

## 30-Second Reading Path

1. Read [`README.md`](../README.md) for the product positioning, quick run, artifact contract, limits, and roadmap.
2. Inspect `src/deep_research_agent/` for the canonical runtime.
3. Inspect `evals/reports/phase5_local_smoke/` for the merge-safe smoke gate.
4. Read [`docs/final/EXPERIMENT_SUMMARY.md`](./final/EXPERIMENT_SUMMARY.md) and [`docs/benchmarks/native/README.md`](./benchmarks/native/README.md) for evaluation evidence.

## Root Classification

| Path | Classification | Meaning |
| --- | --- | --- |
| `src/deep_research_agent/` | canonical | The one implementation source of truth: agents, gateway, orchestration, kernel, auditor, reporting, product, corpus, providers, evals. |
| `main.py` | canonical | Thin CLI wrapper around `deep_research_agent.gateway.cli`. |
| `apps/` | UI roots | `apps/gui-web/` (React product workspace), `apps/demo-site/` (static GitHub Pages demo), `apps/desktop-tauri/` (experimental desktop shell). |
| `desktop/` | retired path | The former `desktop/tauri/` wrapper moved to `apps/desktop-tauri/`; no current code lives at this root. |
| `configs/` | active | Runtime, source profile, provider, domain-pack, and release-gate configuration. |
| `schemas/` | active | JSON schemas for artifact, audit, runtime, connector, and benchmark contracts. |
| `tests/` | active | Runtime, connector, auditor, public-surface, benchmark, and repo-standard regressions. |
| `scripts/` | active | Release smoke, native regression, benchmark, scorecard, demo-data, and diagnostic commands. |
| `evals/` | active evidence | Suite configs, frozen datasets, rubrics, committed smoke outputs, regression outputs, and derived value packs. |
| `examples/` | pointer | `sample_bundle/` demo bundle; runnable CLI examples are in the README. |
| `migrations/` + `alembic.ini` | active | Alembic migrations for the product database schema. |
| `deploy/` | active | Deployment fragments (web nginx config, GROBID notes); Compose lives at the root. |
| `docs/` | public docs | Reviewer docs, architecture, development guide, ADRs, benchmark docs, GUI docs, final summaries, and archives. |
| `legacy/` | archived | Archived graph-first runtime. It owns its full dependency closure: agents/workflows, `legacy/auditor/`, `legacy/connectors/`, `legacy/llm/`, `legacy/prompts/`, `legacy/policies/`, `legacy/capabilities/`, `legacy/memory/`, `legacy/tools/`, `legacy/evaluation/`, and `legacy/research_policy.py`. Nothing under `legacy/` is product architecture. |
| `.github/` | repo metadata | CI, Pages deployment, issue and PR templates. |
| `.env.example` | setup | Public environment template. |
| `.python-version` | setup | Python version pin. |
| `pyproject.toml` | setup | Package metadata, dependencies, and setuptools `src` layout. |
| `pytest.ini` | setup | Pytest configuration. |
| `uv.lock` | setup | Locked dependency graph for `uv`. |
| `README.md` / `README.zh-CN.md` | public docs | GitHub entrypoints. |
| `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | repo metadata | Community and security files. |
| `AGENTS.md` | automation guidance | Public, repo-safe guidance for coding agents. |

## Legacy Boundary

`legacy/` is the archived graph-first runtime and its dependencies. It is still imported by two
compatibility consumers, both out of the product path:

- `src/deep_research_agent/research_jobs/orchestrator.py` uses `legacy.agents.*` stage functions
  for the `orchestrator-v1` runtime path (default for CLI/API submissions; deterministic
  benchmark profile in offline mode).
- Diagnostic scripts under `scripts/` and a few regression tests import `legacy.evaluation.*`
  and `legacy.research_policy`.

The canonical V2 runtime (`orchestration/`, `kernel/`, `reporting/bundle_v2.py`) never imports
`legacy/`. Future work should retire `orchestrator-v1` once the V2 path covers all CLI/API flows.

## Archived Or Local-Only Material

These were removed from the public reviewer path because they describe local agent execution rather
than the product:

- `.agent/`
- `.agents/`
- `PLANS.md`
- `docs/codex/`
- `docs/refactor/`
- `docs/专家审查意见/`
- `apps/demo-video/`

If they exist in a local checkout, treat them as private development notes, not GitHub product docs.

## Evaluation Report Roots

| Path | Reviewer meaning |
| --- | --- |
| `evals/reports/phase5_local_smoke/` | Merge-safe deterministic smoke gate. |
| `evals/reports/native_regression/` | Deterministic reviewer regression evidence. |
| `evals/reports/followup_metrics/` | Derived value-pack artifacts retained at this path because tests and final docs assert repo-relative artifact paths. |
| `evals/reports/native_optimization/` | Derived before/after optimization artifacts retained at this path because tests and native benchmark docs assert repo-relative artifact paths. |
| `evals/reports/live_agent/` | Live model-driven run evidence: real LLM planner/researcher/critic over governed real-time search; bundle, scheduler checkpoints, and run summary committed. |
| `evals/reports/live_route_demo/` | Live agentic-loop route demo (Hangzhou→Dongguan, three personas): function-calling researcher loop, reflection follow-ups, full-page reads, 261 accepted claims; bundle, report, run summary, and scheduler checkpoints committed. |

## Boundary Rules

- Treat `src/deep_research_agent/` as the implementation source of truth.
- Treat `report_bundle.json` as the authoritative job output.
- Treat `evals/reports/phase5_local_smoke/` as the merge-safe release smoke evidence.
- Treat `evals/reports/native_regression/` and `docs/benchmarks/native/` as deterministic reviewer regression evidence.
- Treat `legacy/` (including its dependency closure) as archived, non-product code.
- Do not reintroduce root-level compatibility shims; tests and scripts import `deep_research_agent.*` or `legacy.*` directly.
