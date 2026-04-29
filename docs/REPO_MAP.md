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
| `evals/` | active evidence | Suite configs, frozen datasets, rubrics, committed smoke outputs, regression outputs, and derived value packs. |
| `apps/gui-web/` | active UI | Optional local web GUI for operator/reviewer workflows over the local API. |
| `apps/desktop-tauri/` | experimental UI wrapper | Optional Tauri desktop shell around the local web GUI; kept under `apps/` because it is not runtime code. |
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
| `artifacts/` | compatibility shim | Remains at root because tests and older imports still use `artifacts.*`; canonical reporting lives in `src/deep_research_agent/reporting/`. |
| `auditor/` | compatibility shim | Remains at root for `auditor.*` imports; canonical audit code lives in `src/deep_research_agent/auditor/`. |
| `connectors/` | compatibility shim | Remains at root for older connector imports; canonical connector code lives in `src/deep_research_agent/connectors/`. |
| `services/` | compatibility shim | Remains at root for `services.research_jobs.*`; canonical runtime lives in `src/deep_research_agent/research_jobs/`. |
| `policies/` | compatibility shim | Remains at root for older policy imports; canonical policy code lives in `src/deep_research_agent/policy/`, and source profiles live in `configs/source_profiles/`. |
| `tools/` | compatibility shim | Remains at root for older tool imports; canonical connector helpers live under `src/deep_research_agent/connectors/tools/`. |
| `llm/` | compatibility shim | Remains at root for legacy provider imports and output-cleaning helpers; canonical provider routing lives in `src/deep_research_agent/providers/`. |
| `memory/` | compatibility / legacy shim | Remains at root for older memory/evidence imports; canonical evidence store lives in `src/deep_research_agent/evidence_store/`. |
| `capabilities/` | legacy diagnostics | Remains at root for archived graph/MCP compatibility tests; not current architecture. |
| `prompts/` | legacy diagnostics | Remains at root for archived graph prompt templates; not current architecture. |
| `evaluation/` | legacy diagnostics | Remains at root because diagnostic scripts and tests import it; current release evidence is under `evals/`. |
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

## Evaluation Report Roots

| Path | Reviewer meaning |
| --- | --- |
| `evals/reports/phase5_local_smoke/` | Merge-safe deterministic smoke gate. |
| `evals/reports/native_regression/` | Deterministic reviewer regression evidence. |
| `evals/reports/followup_metrics/` | Derived value-pack artifacts retained at this path because tests and final docs assert repo-relative artifact paths. |
| `evals/reports/native_optimization/` | Derived before/after optimization artifacts retained at this path because tests and native benchmark docs assert repo-relative artifact paths. |

## Boundary Rules

- Treat `src/deep_research_agent/` as the implementation source of truth.
- Treat `report_bundle.json` as the authoritative job output.
- Treat `evals/reports/phase5_local_smoke/` as the merge-safe release smoke evidence.
- Treat `evals/reports/native_regression/` and `docs/benchmarks/native/` as deterministic reviewer regression evidence.
- Treat root compatibility packages as import-stability shims, not as the primary architecture.
- Treat `legacy/`, `evaluation/`, `capabilities/`, `prompts/`, and archived docs as non-primary paths unless a diagnostic script or compatibility test explicitly targets them.
