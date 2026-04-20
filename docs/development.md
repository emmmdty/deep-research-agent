# 开发指南

> 迁移期内，开发顺序以 `AGENTS.md -> PLANS.md -> 当前 active phase spec` 为准。
> 本文档同时描述当前公开 phase2 orchestrator CLI 与 legacy runtime 的开发/验证方式，不等同于未来产品架构。

## 环境搭建

```bash
# 克隆仓库
git clone https://github.com/emmmdty/deep-research-agent.git
cd deep-research-agent

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API 密钥
```

## 开发流程

### 进入改动前先确认

1. 当前 active phase 是什么。
2. 这次改动服务的是 legacy 维护，还是 phase 迁移目标。
3. 是否触碰了需要 ADR 的边界：
   - 新增 agent 角色
   - 新增持久化核心对象
   - 新增长期架构边界

### 新增 Agent 角色前的限制

默认**不要新增 agent 角色**。若必须新增，先补 ADR，说明：

- 为什么不能下沉为确定性协议或工具层
- 对 job lifecycle、claims、evidence、audit 的影响
- 与现有 legacy runtime 的兼容或迁移策略

### 新增 Agent

1. 在 `agents/` 下创建新文件（如 `agents/my_agent.py`）
2. 定义 LangGraph node 函数：接收 `state: dict` 返回 `dict`
3. 在 `workflows/graph.py` 中注册节点和边；当前 benchmark 主链路默认包含 `Verifier`
4. 如需要，在 `workflows/graph.py` 的 `GraphState` 中添加新的状态字段

注意：

- 以上流程仅适用于维护当前 legacy runtime。
- 若改动目标是未来可信研究架构，应优先在 phase spec 中落地对象合同、编排边界和 connector contract，而不是继续加人格化节点。

### 新增 Capability / Skill / MCP 适配

1. 在 `capabilities/` 中新增或扩展适配器
2. `builtin` 能力需要映射到真实 Python 工具
3. `skill` 兼容以 `SKILL.md` 为根的目录组织
4. `mcp` 当前优先从 `MCP_CONFIG_PATH` 指向的 YAML 配置加载，支持 `stdio / sse / streamable-http`；如未提供文件，再回退到 `MCP_SERVERS` JSON

### 新增 Verifier / Evidence Memory

1. Verifier 节点负责把 `SourceRecord` / `EvidenceNote` 转成 `EvidenceUnit`、`EvidenceCluster`
2. 持久化统一走 `memory/evidence_store.py`
3. 新增记忆或验证字段时，同步更新 `ReportArtifact` 与 benchmark 指标

### 新增工具

1. 在 `tools/` 下创建新文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `tools/__init__.py` 中导出

### 新增提示词

1. 在 `prompts/templates.py` 中添加 `SYSTEM_PROMPT` 和 `USER_PROMPT`
2. User prompt 使用 `{variable}` 格式的占位符

### 新增评估指标

1. 在 `evaluation/metrics.py` 中添加指标函数
2. 若指标需要 `Verifier / Evidence Memory / ReportArtifact` 信号，同步更新 `evaluation/comparators.py`
3. benchmark summary 现在区分 `scorecard`、`legacy_metrics` 与 `benchmark_health`，新增主展示指标时同步更新 `scripts/run_benchmark.py`
4. 如需比较方法收益，优先把变体接入 `scripts/run_ablation.py`，不要只在 README 中做口头描述
5. benchmark profile 下修改 `quality_gate` 时，必须同时校验 `failed_quality_gate` 终态与 comparator 失败语义，避免“gate 失败但仍 completed”
6. `case-study` 相关改动必须同时覆盖：query bundle、官方域名优先、GitHub 一手仓库识别、连续值指标与 summary 展示

## 常用命令

```bash
# 提交 research job
uv run python main.py submit --topic "你的研究主题"
uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
uv run python main.py cancel --job-id <job_id>
uv run python main.py retry --job-id <job_id>

# legacy 直跑（迁移期保留）
uv run python main.py legacy-run --topic "你的研究主题"
uv run python main.py legacy-run --topic "你的研究主题" --profile benchmark

# 运行 Benchmark
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set portfolio12 --summary

# 运行内部 ablation 对照
uv run python scripts/run_ablation.py --topic-set portfolio12 --profile benchmark

# 运行 portfolio12 正式 release（默认 hybrid：代表题 live judge + 全量可复现 benchmark）
uv run python scripts/run_portfolio12_release.py --env-file /绝对路径/.env --topic-set portfolio12 --release-mode hybrid

# 运行 local3 自动优化闭环
uv run python scripts/optimize_local3.py --profile benchmark --max-rounds 3 --skip-judge

# 运行全量 comparator 对比
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba

# 离线文件对比
uv run python scripts/compare_agents.py --file-a our.md --file-b competitor.md
```

说明：
- 公开 CLI 已切到 phase2 orchestrator，`submit/watch/status/cancel/retry` 是默认入口
- phase3 以后，`submit` 还支持 `--source-profile`、`--allow-domain`、`--deny-domain`、`--max-candidates-per-connector`、`--max-fetches-per-task`、`--max-total-fetches`
- phase4 以后，`status --json` 会额外暴露 `audit_gate_status`、关键 claim 计数和 audit artifacts 路径
- `legacy-run` 只用于迁移期验证和维持旧路径可运行，不是长期产品契约
- `--summary` 会生成 `benchmark_summary.json/.md`
- 新版 summary 默认输出 `scorecard`、`legacy_metrics`、`benchmark_health` 和 `judge_status`
- `--skip-judge` 时，`judge_*` 不再写成 `0.0`，而是通过 `judge_status=skipped` 表达“本轮未评分”
- 若当前 worktree 没有本地 `.env`，通过 `--env-file` 显式加载主仓库或外部环境文件
- 正式结果集优先通过 `scripts/run_portfolio12_release.py` 产出；默认 `hybrid` 会对 `T01,T04,T11` 跑 live judge，并生成 `RESULTS.md` 与 `release_manifest.json`
- `case-study / 行业应用案例` 的 benchmark 方面默认只接受 `官方站点 + 一手仓库` 证据；survey / review / benchmark 结果应被拒绝为 `not_case_study_evidence`
- 相关 summary 应补充 `case_study_strength_score_100`、`first_party_case_coverage_100`、`official_case_ratio_100`、`case_study_gate_margin_100`
- benchmark profile 下，若 LLM summary 未满足方面/引用/高可信证据约束，会自动回退为 deterministic summary，并记录 `summary_repair_count`
- 直接用 shell 覆盖列表配置时，优先使用 JSON 数组语法，例如 `ENABLED_SOURCES='["github"]'`

## Phase 01 联网验收

用于确认当前 legacy CLI 在真实联网路径下可以产出合法的 phase 01 bundle。

### 运行最小真实研究任务

```bash
WORKSPACE_DIR=workspace/phase1-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py legacy-run --topic "Datawhale是一个什么样的组织" --max-loops 2
```

预期输出：

- `workspace/phase1-live-validation/report_Datawhale是一个什么样的组织.md`
- `workspace/phase1-live-validation/bundles/<run_id>/report_bundle.json`
- `workspace/phase1-live-validation/bundles/<run_id>/trace.jsonl`

### 校验 bundle 合法性

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
print({"bundle_path": str(bundle_path), "trace_path": str(trace_path)})
PY
```

说明：

- phase 01 允许 `claims` 为 placeholder
- 该验收只要求 bundle、citation、snapshot、audit event 和 trace 真实存在且 schema 合法
- 若 topic 临时不可用，可替换为另一个公开、低成本、web-only 的组织/概念类问题，但输出结构与校验步骤不变

## Phase 02 联网验收

用于确认当前公开 CLI 已切到可恢复 job runtime，并能在真实联网路径下完成一条研究任务。

### 提交并观察真实 job

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

### 校验 job 产物

```bash
uv run python - <<'PY'
import json
import sqlite3
from pathlib import Path

from artifacts.schemas import validate_instance

root = Path("workspace/phase2-live-validation/research_jobs")
db_path = root / "jobs.db"
with sqlite3.connect(db_path) as conn:
    row = conn.execute(
        "SELECT job_id, status, report_bundle_path, trace_path FROM jobs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

assert row is not None
job_id, status, bundle_path, trace_path = row
assert status == "completed"

bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
validate_instance("report-bundle", bundle)

assert Path(trace_path).exists()
assert bundle["job"]["runtime_path"] == "orchestrator-v1"
print({"job_id": job_id, "bundle_path": bundle_path, "trace_path": trace_path})
PY
```

说明：

- phase 02 仍允许 bundle 中的 `claims` 保持 phase1 的 placeholder 形态
- benchmark / comparator 暂时不走 orchestrator runtime
- `needs_review` 只用于恢复异常，不用于一般研究质量问题

## Phase 03 联网验收

用于确认当前公开 CLI 已切到统一 connector substrate，并在真实联网路径下产出真实 snapshot。

### 公开 CLI：source policy + snapshot validation

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

校验命令：

```bash
uv run python - <<'PY'
import json
import sqlite3
from pathlib import Path

from artifacts.schemas import validate_instance

root = Path("workspace/phase3-live-validation/research_jobs")
with sqlite3.connect(root / "jobs.db") as conn:
    row = conn.execute(
        "SELECT job_id, status, report_bundle_path, trace_path FROM jobs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

assert row is not None
job_id, status, bundle_path, trace_path = row
assert status == "completed"

job_root = root / job_id
snapshot_dir = job_root / "snapshots"
bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
validate_instance("report-bundle", bundle)

assert Path(trace_path).exists()
assert snapshot_dir.exists()
assert list(snapshot_dir.glob("*.json"))
assert list(snapshot_dir.glob("*.txt"))
assert bundle["sources"]
assert bundle["snapshots"]
assert all(source["snapshot_ref"] for source in bundle["sources"])
print({"job_id": job_id, "bundle_path": bundle_path, "snapshot_dir": str(snapshot_dir)})
PY
```

### service/internal：file-ingest smoke

公开 CLI 在 phase03 仍不暴露 `--file`。文件接入只通过 service/internal 路径验收：

```bash
uv run python - <<'PY'
from pathlib import Path

from configs.settings import Settings
from services.research_jobs.service import ResearchJobService

workspace = Path("workspace/phase3-file-smoke")
sample = workspace / "inputs" / "sample.md"
sample.parent.mkdir(parents=True, exist_ok=True)
sample.write_text("# LangGraph\n\nLangGraph 是一个用于构建多步骤 agent 工作流的框架。", encoding="utf-8")

service = ResearchJobService(Settings(workspace_dir=str(workspace)))
job = service.submit(
    topic="根据本地文件总结 LangGraph 的定位",
    source_profile="public-then-private",
    file_inputs=[str(sample.resolve())],
)
print(job.job_id)
PY
```

随后对该 job 执行 `watch/status`，并确认 `snapshots/` 下存在 `auth_scope = "private"` 的 manifest。

## Phase 04 回归验收

用于确认当前公开 runtime 已切到 claim-level audit pipeline，并能输出 blocked review queue 与 claim graph。

### 运行 phase04 审计回归

```bash
uv run pytest -q tests/test_phase4_auditor.py
```

预期覆盖：

- `claim_auditing` 新阶段
- blocked critical claim review queue
- `completed + blocked` 语义
- `report_bundle.json` 中的真实 `claims / claim_support_edges / conflict_sets`

### 查看公开 runtime 的审计产物

完成态 job 目录下应出现：

- `workspace/research_jobs/<job_id>/audit/claim_graph.json`
- `workspace/research_jobs/<job_id>/audit/review_queue.json`

若 `status = completed` 且 `audit_gate_status = blocked`，表示：

- runtime 正常完成并生成报告
- 但至少有一条关键 claim 未通过审计门禁
- 报告顶部和 review queue 都应暴露该阻塞事实

## 代码规范

- **Python**: 3.10+，使用类型注解
- **注释**: 中文
- **日志**: 使用 `loguru` 的 `logger.info/warning/error`
- **提交**: 中文 Conventional Commits（`feat:` / `fix:` / `docs:`）
