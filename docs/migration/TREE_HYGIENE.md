# Tree Hygiene Record

This document records the documentation-and-repository-structure hygiene run.

## Purpose

The migration and benchmark work is already complete. This run does not add features, benchmark
logic, provider integrations, or runtime behavior. It makes the GitHub tree clearer for reviewers by
labeling current, compatibility, and legacy boundaries.

## Moved Or Archived

| Source | Destination | Reason |
| --- | --- | --- |
| `PLANS.md` old body | `docs/archive/PLANS-legacy-release-train.md` | The old release-train plan described an earlier migration sequence and was confusing at the repository root. |
| `examples/basic_research.py` | `legacy/examples/basic_research.py` | The script used the graph-first legacy runtime, not the current supported CLI/API/batch surface. |
| `skills/` | `legacy/skills/` | The root skill wrappers were legacy graph-oriented helpers and were not imported by the current runtime. |
| `mcp_servers/` | `legacy/mcp_servers/` | The root package was a placeholder; current MCP configuration lives in `configs/mcp_servers.example.yaml` and compatibility tests. |

## Replaced With Markers

- Root `PLANS.md` now points to the archived plan and current reviewer entrypoints.
- `examples/README.md` points to README-based examples and the archived graph-first script.
- `legacy/README.md`, `legacy/examples/README.md`, `legacy/skills/README.md`, and `legacy/mcp_servers/README.md` label archived material explicitly.

## Labeled In Place

These roots were kept because tests, scripts, compatibility imports, or current config still rely on
them:

- `artifacts/`, `auditor/`, `connectors/`, `services/`, `llm/`, `memory/`, and `tools/` are compatibility/support paths for canonical `src/deep_research_agent/` modules.
- `capabilities/` and `prompts/` support archived graph/runtime paths and compatibility tests.
- `evaluation/` contains older benchmark/comparator diagnostics, not the release gate.
- `policies/` contains active source-profile assets.
- `schemas/` contains active JSON contract schemas.
- `docs/refactor/` and `docs/codex/` are historical planning/refactor notes and templates.

## Not Moved

- `src/` remains the canonical implementation root.
- `evals/` remains the active deterministic eval and benchmark asset root.
- `docs/benchmarks/`, `docs/final/`, and root `FINAL_CHANGE_REPORT.md` remain current reviewer docs.
- `research_policy.py` remains at root because older benchmark tests and scripts still import it.
- Compatibility shims remain at root to avoid breaking imports that are intentionally covered by tests.

## Current Review Boundaries

- `smoke_local` under `evals/reports/phase5_local_smoke/` is the authoritative merge-safe gate.
- `regression_local` under `evals/reports/native_regression/` is the deterministic native regression layer.
- The local HTTP API is implemented but still local-only: SQLite, filesystem artifacts, and local workers.
- The hidden `legacy-run` path and graph-first archive are not the primary runtime.
- External benchmark adapters are smoke/subset-first diagnostics and do not override the native release gate.
