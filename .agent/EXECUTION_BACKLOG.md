# Execution Backlog

## Purpose

本文件冻结本次自治执行 run 的 Phase 0 结论，作为后续 Phase 1-6 的直接执行底稿。

执行基线：

- main baseline commit: `4a7995b6eec6d47a2d84efba750fcd53e55f418c`
- main branch state at phase start: `main...origin/main [ahead 1]`
- control truth: `.agent/context/PROJECT_SPEC.md` + `.agent/context/TASK2_SPEC.yaml`
- active phase files on disk:
  - `.agent/phases/00_phase0_read_and_model.md`
  - `.agent/phases/01_phase1_structure.md`
  - `.agent/phases/02_phase2_runtime_provider.md`
  - `.agent/phases/03_phase3_pipeline.md`
  - `.agent/phases/04_phase4_surface_docs.md`
  - `.agent/phases/05_phase5_evals_release.md`
  - `.agent/phases/06_phase6_finalize.md`

## Frozen Decisions

### 1. Unmapped top-level directories

| Path | Current role | Phase 0 decision | Follow-up phase |
|---|---|---|---|
| `capabilities/` | legacy graph capability routing + MCP discovery | split: migrate MCP runtime into `src/deep_research_agent/connectors/mcp_bridge/`; archive builtin/skill routing with legacy graph | Phase 1 / 3 |
| `prompts/` | legacy agent prompt templates | archive with legacy graph runtime; replace with stage-bounded prompt assets under new package | Phase 1 / 2 |
| `schemas/` | live JSON Schemas used by runtime/tests | keep and re-scope as canonical contract schemas; later move loading/validation into formal schema layer under `src/` | Phase 1 / 2 |
| `examples/` | legacy graph example | re-scope to new CLI/API/batch demos; archive current `basic_research.py` | Phase 4 |
| `skills/` | legacy Python wrappers over `workflows.graph` | archive | Phase 1 |
| `workspace/` | gitignored runtime outputs, snapshots, eval artifacts | keep as runtime/eval data root only; never treat as source tree | all phases |

### 2. Source profile migration

Canonical target names:

- `company_trusted`
- `company_broad`
- `industry_trusted`
- `industry_broad`
- `public_then_private`
- `trusted_only`

Migration strategy:

- public surface, docs, configs, CLI, API, bundle metadata, and tests switch to canonical names only
- temporary read-compat aliases are allowed only inside migration adapters/config loaders
- alias mapping:
  - `open-web` -> `company_broad`
  - `trusted-web` -> `company_trusted`
  - `public-then-private` -> `public_then_private`
- `industry_trusted`, `industry_broad`, and `trusted_only` are new first-class profiles to add during policy migration
- do not keep legacy names in README, CLI help, API schema, or release artifacts once migrated

### 3. Documentation authority

- `.agent/context/*` remains the implementation source of truth
- updated `docs/` and README become the public truth as phases land
- `specs/api-readiness-contract.md` and `specs/evaluation-protocol.md` remain active migration references until their content is absorbed into the new surfaces
- `PLANS.md` and the old `specs/phase-*.md` become migration diagnostics, not control-layer execution truth

## Live Repo Grounding

### Keep

- `services/research_jobs/` state machine ideas, lease/recovery logic, event/checkpoint store
- `connectors/models.py`
- `connectors/snapshot_store.py`
- `connectors/utils.py`
- `connectors/files.py`
- `policies/source_policy.py`
- `policies/budget_guardrails.py`
- `policies/models.py`
- `policies/source-profiles/` as migration seed data
- `auditor/models.py`
- `auditor/pipeline.py` claim/support/conflict primitives
- `artifacts/` bundle/schema helpers as migration seed
- `memory/evidence_store.py`
- `tools/web_search.py`
- `tools/github_search.py`
- `tools/arxiv_search.py`
- `tests/test_phase2_jobs.py`
- `tests/test_phase3_connectors.py`
- `tests/test_phase4_auditor.py`
- `tests/test_release_gate.py`
- `tests/test_public_repo_standards.py`
- `main.py` only as transitional thin wrapper target

### Migrate

- `services/research_jobs/ -> src/deep_research_agent/research_jobs/`
- `connectors/ -> src/deep_research_agent/connectors/`
- `policies/ -> src/deep_research_agent/policy/`
- `auditor/ -> src/deep_research_agent/auditor/`
- `artifacts/ -> src/deep_research_agent/reporting/`
- `llm/provider.py -> src/deep_research_agent/providers/`
- `memory/evidence_store.py -> src/deep_research_agent/evidence_store/`
- `schemas/ + artifacts/schemas.py -> src/deep_research_agent/common/schemas/` or equivalent formal schema layer
- `evaluation/ + release/eval scripts -> evals/`
- `configs/settings.py -> new config/provider/runtime profile layout`

### Archive

- `agents/`
- `workflows/`
- `prompts/`
- `skills/`
- `memory/store.py`
- `mcp_servers/` placeholder content
- legacy comparator narrative and old benchmark positioning docs
- old report-shape metric logic once claim-centric replacements land
- non-MCP parts of `capabilities/`

### Delete or Replace

- `needs_review` as lifecycle terminal status
- README/pyproject LangGraph + multi-agent product positioning
- old source profile names in public contracts
- release claims that HTTP API is unsupported after Phase 4 lands
- release logic that treats word count / section count / raw citation count as ship criteria
- tests that permanently enforce "no FastAPI / no HTTP server" after the new API exists

## File Impact Map

### Phase 1 - structure rebuild

- `pyproject.toml`
- `main.py`
- `README.md`
- `README.zh-CN.md`
- `src/deep_research_agent/` new package tree
- `legacy/` archive tree
- moved package modules and import sites across runtime/policy/connectors/auditor/reporting

### Phase 2 - runtime and providers

- `src/deep_research_agent/research_jobs/**`
- `src/deep_research_agent/providers/**`
- `src/deep_research_agent/common/**`
- `configs/**`
- `tests/unit/**` or migrated runtime/provider tests
- old callers still importing `services.research_jobs` or `llm.provider`

### Phase 3 - pipeline

- `src/deep_research_agent/connectors/**`
- `src/deep_research_agent/policy/**`
- `src/deep_research_agent/evidence_store/**`
- `src/deep_research_agent/auditor/**`
- `src/deep_research_agent/reporting/**`
- contract schemas
- integration tests and bundle/artifact validation

### Phase 4 - public surfaces and docs

- `src/deep_research_agent/gateway/**`
- `main.py`
- CLI entrypoints in package metadata
- `docs/architecture.md`
- `docs/development.md`
- `docs/evaluation.md`
- `docs/migration.md`
- `docs/adr/*.md`
- demo/example files

### Phase 5 - evals and release gates

- `evals/**`
- migrated test layout
- `configs/release_gates/**` or equivalent
- release gate runner and manifests
- removal/rewrite of obsolete readiness tests

### Phase 6 - finalize

- `FINAL_CHANGE_REPORT.md`
- experiment/result summary docs
- final README/docs cleanup

## First P0 Implementation Tranche

先完成能让后续 phases 不再被旧边界阻塞的最小纵切：

1. 建立 `src/deep_research_agent/` 包根和新 public entrypoint。
2. 把 runtime / connectors / policy / auditor / reporting / providers 的 canonical import path 立起来。
3. 让 `main.py` 只做 thin wrapper。
4. 把 legacy graph、legacy prompts、legacy skill wrappers、toy memory 明确归档。
5. 让新的 runtime model 去掉 `needs_review`，补上 `resume/refine` 与分离的 `audit_gate_status`。

## Risks

- 现有测试大量绑定旧路径，迁移时需要分阶段重写而不是一次性硬切。
- `tests/test_phase6_api_readiness.py` 当前强制“没有 HTTP API”，Phase 4 后必须删除或替换，否则会系统性阻塞目标实现。
- 当前 provider/config surface 偏 OpenAI-compatible；Anthropic 原生支持会牵动 config、routing、docs、tests。
- `capabilities/` 与 `prompts/` 深度耦合 `agents/` / `workflows/`，结构迁移时容易出现残余 import。
- `workspace/` 为共享 symlink，本地 smoke 必须使用 phase-specific `WORKSPACE_DIR` 或 isolated temp path，避免污染历史产物。

## Command Registry

- lint:
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- format_check:
  `not configured separately in current repo`
- typecheck:
  `not configured in current repo`
- test_collect:
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q`
- unit_tests:
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`
- focused_runtime_regressions:
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py`
- cli_smoke:
  `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- legacy_eval_runner_baseline:
  `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary`
- api_smoke:
  `not applicable before Phase 4; to be replaced with FastAPI smoke once implemented`
- build:
  `none documented`

## Phase Acceptance Commands

### Phase 0

- `test -f .agent/EXECUTION_BACKLOG.md`
- `rg -n "Frozen Decisions|File Impact Map|Phase Acceptance Commands" .agent/EXECUTION_BACKLOG.md`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`

### Phase 1

- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import deep_research_agent; print(deep_research_agent.__file__)"`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- best available focused import/path tests after migration

### Phase 2

- runtime/provider focused suites
- lifecycle smoke for submit/status/cancel/retry/resume/refine
- provider config/routing unit tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`

### Phase 3

- connector/policy/snapshot integration tests
- claim/audit/reporting integration tests
- one frozen or synthetic end-to-end research job smoke with real artifacts
- bundle/schema validation

### Phase 4

- API smoke tests against the new HTTP surface
- CLI smoke tests for canonical commands
- batch path smoke
- request/response schema validation

### Phase 5

- lint
- unit tests
- integration tests
- e2e smoke
- one reliability suite
- one policy/security suite
- one file-ingest suite
- one company task and one industry task emitting bundles
- release gate manifest generation

### Phase 6

- final lint/smoke subset on `main`
- final CLI/API demo command checks
- final artifact path checks
- final report/doc existence checks

## Local-only Bootstrap Policy

Every fresh worktree must explicitly inspect and handle:

- `.env`
- `.venv`
- `.python-version`
- `.codex/config.toml`
- `workspace/`
- `venv_gptr/`

Current safe bootstrap method:

- symlink `.env`
- symlink `.venv`
- keep tracked `.python-version`
- symlink `.codex/config.toml`
- symlink `workspace/`
- symlink `venv_gptr/`

Note: any phase that writes runtime artifacts must override workspace/output locations to avoid cross-phase artifact collisions.
