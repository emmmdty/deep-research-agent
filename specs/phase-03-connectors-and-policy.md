# Phase 03 — Connector Substrate, Snapshotting, and Source Policy

## Status

- Completed

## Objective

统一 search / fetch / file-ingest 连接层，建立 snapshot 与 source policy 体系。

## Why This Phase Exists

没有 connector substrate，就没有可信 provenance，也无法做 public/private staged research、来源治理与 connector health 观测。

## Scope In

- open web、files、GitHub、arXiv 接入统一接口
- snapshot store
- source profiles：`open-web`、`trusted-web`、`public-then-private`
- domain allow / deny
- budget caps

## Scope Out

- 大规模企业应用 catalog
- 通用 browser agent
- 任意站点自动登录

## Required Deliverables

- `connectors/` 统一接口
- `policies/source-profiles/`
- snapshot hashing / canonicalization
- connector health metrics
- `LegacyConnectorAdapter` 兼容层（如需要）

## Contract Rules

所有 connector 至少统一产出：

- `source_id`
- `canonical_uri`
- `fetched_at`
- `content_hash`
- `mime_type`
- `auth_scope`
- `freshness_metadata`
- `snapshot_ref`

## Validation

- URL / file / GitHub / arXiv 样本抓取
- policy enforcement tests
- freshness metadata presence tests
- seeded malicious page handling smoke tests

## Live Acceptance Procedure

### 公开 CLI：GitHub-only 低成本验收

```bash
WORKSPACE_DIR=workspace/phase3-live-validation \
ENABLED_SOURCES='["github"]' \
uv run python main.py submit \
  --topic "langgraph github repository" \
  --source-profile trusted-web \
  --allow-domain github.com \
  --max-candidates-per-connector 3 \
  --max-fetches-per-task 2 \
  --max-total-fetches 4
uv run python main.py watch --job-id <job_id>
```

预期输出：

- `workspace/phase3-live-validation/research_jobs/jobs.db`
- `workspace/phase3-live-validation/research_jobs/<job_id>/report.md`
- `workspace/phase3-live-validation/research_jobs/<job_id>/bundle/report_bundle.json`
- `workspace/phase3-live-validation/research_jobs/<job_id>/bundle/trace.jsonl`
- `workspace/phase3-live-validation/research_jobs/<job_id>/snapshots/*.json`
- `workspace/phase3-live-validation/research_jobs/<job_id>/snapshots/*.txt`

校验要点：

- `report_bundle.json` 通过 `report-bundle.schema.json`
- bundle 中每个 `source.snapshot_ref` 都能在 job 目录下的 snapshot manifest 找到
- snapshot manifest 数量与 bundle snapshots 数量一致

### service/internal：file-ingest smoke

内部文件接入不通过公开 CLI 验收。至少需要一条 `public-then-private` 路径，确认：

- 本地 `.md/.txt/.pdf` 可经 `files` connector ingest
- snapshot 落在 `research_jobs/<job_id>/snapshots/`
- snapshot manifest 中出现 `auth_scope = "private"`

## Metrics

- core connector success rate: `>=95%`
- snapshot completeness: `>=98%`
- freshness metadata presence: `>=99%`
- source policy violation rate: `0`

## Exit Criteria

- 核心来源都经过统一 search/fetch 路径
- 每份证据都有 `snapshot_ref`
- source profile 与 policy enforcement 已生效

## Completion Evidence

- phase03 connector / policy / snapshot 相关回归测试已完成，包含 `connector substrate`、`policy enforcement`、`real snapshot bundle` 和 `job-dir snapshot persistence`
- 真实公开 CLI 验收已在 `2026-04-09` 完成，成功 job 为 `20260409T155216Z-a465b9f6`
- live 产物位于 `workspace/phase3-live-validation-github-v2/research_jobs/20260409T155216Z-a465b9f6/`
- 该 job 的 `report_bundle.json` 已通过 `report-bundle.schema.json` 校验，并与 job 目录下 `4` 份 snapshot manifests / `4` 份 snapshot texts 对齐
- service/internal file-ingest smoke 已在 `2026-04-09` 完成，成功 job 为 `20260409T155333Z-11c1b90e`
- internal smoke 产物位于 `workspace/phase3-file-smoke-v3/research_jobs/20260409T155333Z-11c1b90e/`
- 该 job 目录下已生成 `auth_scope = "private"` 的 snapshot manifest，证明 `public-then-private` 路径可落盘私有文件快照

## Risks

- canonical URL 归一难度
- 动态网页与 PDF span 定位的一致性

## Containment

统一不了的来源允许通过 `LegacyConnectorAdapter` 暂挂，但不得绕过 snapshot 记录与 policy 检查。
