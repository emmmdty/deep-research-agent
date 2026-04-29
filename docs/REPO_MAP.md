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
| `src/` | canonical | Main Python package: gateway, runtime, connectors, policy, auditor, reporting, providers, evals. |
| `main.py` | canonical | Thin CLI wrapper around `deep_research_agent.gateway.cli`. |
| `configs/` | active | Runtime, source profile, provider, and release-gate configuration. |
| `schemas/` | active | JSON schemas for artifacts, audit, runtime, connector, and benchmark contracts. |
| `tests/` | active | Runtime, connector, auditor, public-surface, benchmark, and repo-standard regressions. |
| `scripts/` | active | Release smoke, native regression, benchmark, scorecard, and diagnostic commands. |
| `evals/` | active | Suite configs, frozen datasets, rubrics, committed smoke and regression outputs. |
| `apps/` | active UI | Local web GUI for operator/reviewer workflows over the local API. |
| `desktop/` | active wrapper | Tauri desktop shell around the local web GUI. |
| `docs/` | public docs | Reviewer docs, architecture, development guide, ADRs, benchmark docs, GUI docs, final summaries, and archives. |
| `.github/` | repo metadata | CI, issue templates, and pull request template. |
| `.env.example` | setup | Public environment template. |
| `.python-version` | setup | Python version pin. |
| `pyproject.toml` | setup | Package metadata, dependencies, and setuptools `src` layout. |
| `pytest.ini` | setup | Pytest configuration. |
| `uv.lock` | setup | Locked dependency graph for `uv`. |
| `README.md` / `README.zh-CN.md` | public docs | GitHub entrypoints. |
| `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | repo metadata | Community and security files. |
| `AGENTS.md` | automation guidance | Public, repo-safe guidance for coding agents. |
| `artifacts/` | compatibility | Legacy imports forwarding to canonical reporting modules. |
| `auditor/` | compatibility | Legacy imports forwarding to canonical auditor modules. |
| `connectors/` | compatibility | Legacy imports forwarding to canonical connector modules. |
| `services/` | compatibility | Legacy imports forwarding to canonical research job modules. |
| `policies/` | compatibility | Legacy imports forwarding to canonical policy modules; source profiles now live in `configs/source_profiles/`. |
| `tools/` | compatibility | Legacy imports forwarding to canonical connector helper tools. |
| `llm/` | compatibility | Legacy provider import wrapper and output cleaning helpers. |
| `memory/` | compatibility / legacy | Evidence-store wrapper plus legacy file-memory helper. |
| `capabilities/` | legacy diagnostic support | Capability, skill, and MCP compatibility layer for archived graph paths and tests. |
| `prompts/` | legacy diagnostic support | Prompt templates used by archived graph runtime. |
| `evaluation/` | legacy diagnostics | Older comparator, judge, cost, and report-shape metric helpers. |
| `research_policy.py` | legacy diagnostics | Deterministic benchmark-profile policy helpers retained for older tests and scripts. |
| `legacy/` | archived | Archived graph agents/workflows, old examples, skill wrappers, and placeholder MCP package. |
| `examples/` | pointer | Current runnable examples are in README; old graph example is archived under `legacy/examples/`. |
| `specs/` | historical contracts | Phase specs plus current API/evaluation contracts retained for link stability. |

## Archived Or Local-Only Material

These were removed from the public reviewer path because they describe local agent execution rather
than the product:

- `.agent/`
- `.agents/`
- `PLANS.md`
- `docs/codex/`
- `docs/refactor/`
- `docs/专家审查意见/`

If they exist in a local checkout, treat them as private development notes, not GitHub product docs.

## Boundary Rules

- Treat `src/deep_research_agent/` as the implementation source of truth.
- Treat `report_bundle.json` as the authoritative job output.
- Treat `evals/reports/phase5_local_smoke/` as the merge-safe release smoke evidence.
- Treat `evals/reports/native_regression/` and `docs/benchmarks/native/` as deterministic reviewer regression evidence.
- Treat root compatibility packages as import-stability shims, not as the primary architecture.
- Treat `legacy/`, `evaluation/`, `capabilities/`, `prompts/`, and archived docs as non-primary paths unless a diagnostic script or compatibility test explicitly targets them.
