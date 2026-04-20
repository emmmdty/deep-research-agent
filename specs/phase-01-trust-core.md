# Phase 01 — Trust Core Contracts and Legacy Isolation

## Status

- Completed

## Objective

建立可信研究运行的第一套长期 source of truth：

- versioned schemas
- minimal trace output
- minimal report bundle
- explicit legacy / future boundary

## Why This Phase Exists

当前仓库有 legacy workflow 和报告输出，但没有稳定的可信研究对象模型。后续服务化、连接器、审核、报告与评测都依赖统一 contracts。

## Scope In

- 路线与数据合同 ADR
- 核心对象 schema
- legacy migration map
- tracing / bundling wrapper
- schema validation 与 bundle generation tests

## Scope Out

- HTTP API
- web UI
- connector expansion
- new agent roles
- prompt redesign
- major runtime refactor

## Required Deliverables

- `docs/adr/adr-0001-product-route.md`
- `docs/adr/adr-0002-trust-data-contracts.md`
- `legacy/migration-map.md`
- `schemas/research-job.schema.json`
- `schemas/plan-step.schema.json`
- `schemas/source-document.schema.json`
- `schemas/source-snapshot.schema.json`
- `schemas/evidence-fragment.schema.json`
- `schemas/claim.schema.json`
- `schemas/claim-support.schema.json`
- `schemas/conflict-set.schema.json`
- `schemas/audit-event.schema.json`
- `schemas/report-bundle.schema.json`
- 一份 golden `report_bundle` fixture
- 一条 end-to-end 本地路径，能输出合法 bundle

## Required Object Minimums

### ResearchJob

必须包含：

- `job_id`
- `created_at`
- `input_prompt`
- `status`
- `source_profile`
- `budget`
- `runtime_path`
- `report_bundle_ref`

### SourceSnapshot

必须包含：

- `snapshot_id`
- `canonical_uri`
- `fetched_at`
- `content_hash`
- `mime_type`
- `auth_scope`
- `freshness_metadata`

### EvidenceFragment

必须包含：

- `evidence_id`
- `snapshot_id`
- `locator`
- `excerpt`
- `extraction_method`

### Claim

必须包含：

- `claim_id`
- `text`
- `criticality`
- `uncertainty`
- `status`

### AuditEvent

必须包含：

- `event_id`
- `job_id`
- `stage`
- `event_type`
- `timestamp`
- `payload`

### ReportBundle

必须包含：

- `bundle_version`
- `job`
- `citations`
- `sources`
- `audit_summary`
- `report_text`
- `claims`

phase 01 允许 `claims` 使用明确标记的 placeholder，但不能跳过 source snapshots、citations、run metadata 与 audit events。

## Implementation Guidance

- 在当前 run path 上加**最薄的** wrapper
- 不要求 phase 01 就把 claim extraction 做完美
- 优先保证 bundle 合法、字段真实、legacy 边界清楚
- `workflows/graph.py` 必须显式标为 legacy runtime

## Validation

必须具备：

- schema validation tests
- golden bundle fixture validates
- tracing disabled compatibility test passes
- 一条 end-to-end smoke path 能写出合法 `report_bundle.json`

## Live Acceptance Procedure

使用真实联网路径验证当前 legacy CLI 可以产出合法的 phase 01 bundle：

```bash
WORKSPACE_DIR=workspace/phase1-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py legacy-run --topic "Datawhale是一个什么样的组织" --max-loops 2
```

预期输出：

- `workspace/phase1-live-validation/report_Datawhale是一个什么样的组织.md`
- `workspace/phase1-live-validation/bundles/<run_id>/report_bundle.json`
- `workspace/phase1-live-validation/bundles/<run_id>/trace.jsonl`

校验命令：

```bash
uv run python - <<'PY'
import json
from pathlib import Path

from artifacts.schemas import validate_instance

bundle_root = Path("workspace/phase1-live-validation/bundles")
bundle_path = sorted(bundle_root.glob("*/report_bundle.json"))[-1]
trace_path = bundle_path.with_name("trace.jsonl")
bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

validate_instance("report-bundle", bundle)

assert bundle["report_text"].strip()
assert bundle["citations"]
assert bundle["sources"]
assert bundle["snapshots"]
assert bundle["evidence_fragments"]
assert bundle["audit_events"]
assert trace_path.exists()
PY
```

phase 01 允许 `claims` 为 placeholder；该验收只要求 bundle、citation、snapshot、audit event 和 trace 真实存在且 schema 合法。

## Metrics

- schema coverage: `100%`
- tool event trace coverage: `>=95%`
- citation structuring coverage: `>=90%`
- end-to-end bundle generation: `>=1` 条工作路径

## Exit Criteria

- required files 全部存在
- tests 通过
- legacy boundary 已文档化
- 一条真实研究 run 能产出合法 `report_bundle.json`

## Completion Evidence

- `uv run pytest -q`：`116 passed, 1 skipped`
- 真实联网 run 已在 `2026-04-09` 完成，输出位于 `workspace/phase1-live-validation/bundles/20260409T143117Z-fa690db5/`
- live bundle 通过 `report-bundle.schema.json` 校验，包含 `40` 条 citations、`40` 条 sources、`40` 条 snapshots、`6` 条 placeholder claims

## Risks

- claim extraction 可能过早要求过高
- 现有报告输出未必能稳定映射到结构化 citations
- legacy runtime 可能隐藏隐式状态

## Containment

若 full claim extraction 不可行，可临时使用 placeholder claim list；但不能跳过 `SourceSnapshot`、`AuditEvent`、citation entries。
