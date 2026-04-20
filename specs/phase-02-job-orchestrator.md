# Phase 02 — Resumable Research Job Orchestrator

## Status

- Completed

## Objective

把当前一次性本地执行改为可恢复、可取消、可查询状态的 job runtime。

## Why This Phase Exists

分钟级 deep research 任务需要后台异步执行、状态查询和恢复能力。没有 job orchestration，就无法稳定承载 UI、connector、审计和导出。

## Scope In

- job state machine
- checkpoint store
- progress events
- cancel / retry
- status / query interface
- CLI thin client：`submit / watch / cancel`

## Scope Out

- 企业连接器
- 复杂权限 UI
- 完整多租户管理

## Required Deliverables

- `services/research_jobs/`
- checkpoint store
- event log
- status / query interface
- CLI 改为 submit/watch/cancel 模式

## Runtime Model

推荐状态：

- `created`
- `clarifying`
- `planned`
- `collecting`
- `extracting`
- `auditing`
- `rendering`
- `completed`
- `failed`
- `cancelled`
- `needs_review`

每个阶段都必须产出结构化中间物，并允许 `resume from checkpoint`。

## Validation

- 中途杀进程后 resume
- cancel / retry integration tests
- progress event contract tests
- 连续本地任务无 orphaned job

## Live Acceptance Procedure

```bash
WORKSPACE_DIR=workspace/phase2-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py submit --topic "Datawhale是一个什么样的组织"
uv run python main.py watch --job-id <job_id>
```

预期输出：

- `workspace/phase2-live-validation/research_jobs/jobs.db`
- `workspace/phase2-live-validation/research_jobs/<job_id>/report.md`
- `workspace/phase2-live-validation/research_jobs/<job_id>/bundle/report_bundle.json`
- `workspace/phase2-live-validation/research_jobs/<job_id>/bundle/trace.jsonl`

并执行：

```bash
uv run python - <<'PY'
import json
import sqlite3
from pathlib import Path

from artifacts.schemas import validate_instance

root = Path("workspace/phase2-live-validation/research_jobs")
with sqlite3.connect(root / "jobs.db") as conn:
    row = conn.execute(
        "SELECT job_id, status, report_bundle_path, trace_path FROM jobs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

assert row is not None
job_id, status, bundle_path, trace_path = row
assert status == "completed"

bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
validate_instance("report-bundle", bundle)
assert bundle["job"]["runtime_path"] == "orchestrator-v1"
assert Path(trace_path).exists()
print({"job_id": job_id, "bundle_path": bundle_path, "trace_path": trace_path})
PY
```

## Metrics

- resume success rate: `>=90%`
- cancel response time: `<=10s`
- status persistence coverage: `100%`
- `20` 个连续本地任务无 orphaned job

## Exit Criteria

- 任务可跨进程恢复
- CLI 不再直接持有研究主循环
- 关键 job 状态可查询、可取消、可重试

## Completion Evidence

- 已新增 `services/research_jobs/`、runtime schemas、ADR 和回归测试
- `main.py --help` 已切到 `submit / status / watch / cancel / retry`
- phase2 相关回归测试已覆盖 schema、store、orchestrator、cancel/retry 和 CLI 调度
- 真实联网验收已在 `2026-04-09` 完成，成功 job 为 `20260409T150002Z-3d02fa46`
- live 产物位于 `workspace/phase2-live-validation/research_jobs/20260409T150002Z-3d02fa46/`
- 该 job 的 `report_bundle.json` 已通过 `report-bundle.schema.json` 校验，`job.runtime_path = orchestrator-v1`

## Risks

- 现有 LangGraph 状态可能不适合平滑 checkpoint
- legacy 与新 orchestrator 可能需要并行运行一段时间

## Containment

以 feature flag 保留 legacy CLI path；新 orchestrator 默认只承载新入口，不强制立即替换所有旧路径。
