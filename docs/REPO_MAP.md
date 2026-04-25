# Repository Map

This map is for first-time reviewers. The current implementation is not root-package-first; the
canonical runtime lives under `src/deep_research_agent/`.

## Where To Start

1. Read [`README.md`](../README.md) for the project summary and runnable commands.
2. Read [`DOCS_INDEX.md`](./DOCS_INDEX.md) for the reviewer-facing documentation order.
3. Inspect `src/deep_research_agent/` for canonical implementation code.
4. Inspect `evals/reports/phase5_local_smoke/` for the merge-safe smoke gate.
5. Inspect `docs/benchmarks/native/` and `evals/reports/native_regression/` for native regression evidence.

## Current Root Areas

| Path | Classification | Meaning |
| --- | --- | --- |
| `.agent/` | canonical operations record | Run specs, phase ledgers, status files, and historical automation notes. |
| `.github/` | canonical repo metadata | CI, issue templates, and pull request template. |
| `src/` | canonical current implementation | Main Python package: gateway, runtime, connectors, auditor, reporting, providers, evals. |
| `main.py` | canonical current entrypoint | Thin wrapper around `deep_research_agent.gateway.cli`. |
| `apps/` | canonical current UI surface | Local web GUI under `apps/gui-web/` for operator/reviewer workflows over the local API. |
| `desktop/` | canonical current desktop wrapper | Tauri desktop shell under `desktop/tauri/` around the local web GUI. |
| `configs/` | canonical current config | Runtime settings, release gate config, MCP example config. |
| `policies/` | active policy assets | Source profiles and policy helpers used by current runtime. |
| `schemas/` | active contract schemas | JSON schemas for bundle, audit, runtime, connector, and benchmark artifacts. |
| `evals/` | active benchmark/eval assets | Suite configs, frozen datasets, rubrics, committed smoke and regression outputs. |
| `scripts/` | active command wrappers | Release smoke, native regression, benchmark, scorecard, and diagnostic commands. |
| `tests/` | canonical validation assets | Runtime, connector, auditor, public surface, benchmark, and repo-standard regressions. |
| `docs/` | canonical current docs plus archives | Reviewer docs, final reports, ADRs, benchmark docs, migration notes, and labeled historical notes. |
| `FINAL_CHANGE_REPORT.md` | canonical current docs | Final architecture migration and evidence summary. |
| `README.md` | canonical current docs | Main GitHub entrypoint in English. |
| `README.zh-CN.md` | canonical current docs | Main GitHub entrypoint in Chinese. |
| `artifacts/` | compatibility shim | Legacy imports forwarding to canonical reporting modules. |
| `auditor/` | compatibility shim | Legacy imports forwarding to canonical auditor modules. |
| `connectors/` | compatibility shim | Legacy imports forwarding to canonical connector modules. |
| `services/` | compatibility shim | Legacy imports forwarding to canonical research job modules. |
| `llm/` | compatibility shim | Legacy provider import wrapper plus output cleaning helpers. |
| `memory/` | compatibility and legacy | Evidence-store wrapper plus legacy file-memory helper. |
| `tools/` | compatibility support | Search/fetch helper tools still adapted by the connector layer. |
| `capabilities/` | legacy diagnostic support | Capability, skill, and MCP compatibility layer used by archived graph paths and tests. |
| `prompts/` | legacy diagnostic support | Prompt templates used by archived graph runtime. |
| `evaluation/` | legacy benchmark diagnostics | Older comparator, judge, cost, and report-shape metric helpers. |
| `research_policy.py` | legacy benchmark diagnostics | Deterministic benchmark-profile policy helpers retained for older tests and scripts. |
| `legacy/` | legacy archive | Archived graph agents/workflows, old examples, skill wrappers, and placeholder MCP package. |
| `examples/` | explicit pointer only | Current examples live in the README; old graph example is archived under `legacy/examples/`. |
| `specs/` | historical and contract docs | Phase specs plus current API/evaluation contracts retained for link stability. |
| `PLANS.md` | historical marker | Points to the archived old release-train plan and current reviewer entrypoints. |
| `.env.example` | canonical setup file | Public environment template. |
| `.gitignore` | canonical repo metadata | Protects local secrets, runtime outputs, caches, and lockfile tracking. |
| `.python-version` | canonical setup file | Python version pin for local tooling. |
| `pyproject.toml` | canonical setup file | Package metadata, dependencies, and setuptools layout. |
| `pytest.ini` | canonical setup file | Pytest config. |
| `uv.lock` | canonical setup file | Locked dependency graph for `uv`. |
| `LICENSE` | canonical repo metadata | MIT license. |
| `CONTRIBUTING.md` | canonical repo metadata | Contribution guidance. |
| `CODE_OF_CONDUCT.md` | canonical repo metadata | Community conduct policy. |
| `SECURITY.md` | canonical repo metadata | Security reporting policy. |
| `AGENTS.md` | canonical automation instructions | Repository-specific instructions for automation agents. |

## Ignored Local Areas

These may appear locally but are not part of the GitHub source tree:

- `.env`, `.venv/`, `.codex/`, `workspace/`, and `venv_gptr/`
- cache directories such as `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, and `*.egg-info/`
- ignored Windows metadata files such as `*:Zone.Identifier`
- ignored legacy directory shells such as local `agents/` or `workflows/` cache remnants

Do not delete or commit these during repository hygiene work.

## Boundary Rules

- Treat `src/deep_research_agent/` as the implementation source of truth.
- Treat `apps/gui-web/` and `desktop/tauri/` as supported local operator surfaces, not as archived experiments.
- Treat `evals/reports/phase5_local_smoke/` as the merge-safe release smoke evidence.
- Treat `evals/reports/native_regression/` and `docs/benchmarks/native/` as deterministic reviewer regression evidence.
- Treat root compatibility packages as import-stability shims, not as the primary architecture.
- Treat `legacy/`, `evaluation/`, `capabilities/`, `prompts/`, and archived material as non-primary paths unless a test or diagnostic script explicitly targets them.
