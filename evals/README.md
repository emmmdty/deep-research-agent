# Evals

Canonical evaluation assets for the deterministic deep research runtime.

This tree is the Phase 5 source of truth for:

- suite definitions under `evals/suites/`
- frozen low-cost datasets under `evals/datasets/`
- rubric metadata under `evals/rubrics/`
- committed local smoke outputs under `evals/reports/`
- committed deterministic native regression outputs under `evals/reports/native_regression/`

The runnable local entrypoints are:

- `uv run python main.py eval run --suite company12`
- `uv run python main.py eval run --suite industry12`
- `uv run python main.py eval run --suite trusted8`
- `uv run python main.py eval run --suite file8`
- `uv run python main.py eval run --suite recovery6`
- `uv run python scripts/run_local_release_smoke.py`
- `uv run python main.py eval run --suite company12 --variant regression_local`
- `uv run python scripts/run_native_regression.py`
- `uv run python scripts/build_native_benchmark_summary.py`

## DRB（Deep Research Bench）官方评测

适配器：`src/deep_research_agent/evals/external/benchmarks/drb.py`，注册名为 `drb`
（`benchmark run --benchmark drb` 自动暴露）。引用真实性门禁：
`uv run python scripts/run_drb_gate.py`（阈值见 `evals/external/configs/drb_gate.yaml`，
scorecard 落 `evals/reports/drb_gate/scorecard.json`）。

### 官方数据集来源、许可与格式

- **论文**：Deep Research Bench: Evaluating AI Web Research Agents（FutureSearch，
  Bosse et al.，arXiv:2506.06287，2025-05）。**DRB-II**（rubric 式，132 任务/22 领域，
  9430 条细粒度 rubric）见 arXiv:2601.08536。
- **内容与格式**：多步开放网络研究任务，按任务类型分 8 类（Find Number / Find Dataset /
  Find Original Source / Validate Claim / Derive Number / Gather Evidence /
  Populate Reference Class / Compile Dataset）。每个实例配 10k-100k 网页的 **RetroSearch
  冻结语料**（模拟 Serper/Google 搜索形态，Common Crawl 兜底）与人工精修参考答案。官方评分：
  binary（0/1）、recall、F1、absolute difference（论文 Table 3）。
- **许可**：论文 CC BY-NC-SA 4.0。
- **获取方式**：官方出于防数据污染考虑**不公开全量实例**；评测运行需联系
  `evals@futuresearch.ai`，排行榜见 <https://drb.futuresearch.ai/>。
  仓库内 `evals/external/configs/drb_supported_smoke.yaml` +
  `evals/external/dataset_manifests/drb_supported_smoke.json` +
  `evals/datasets/drb_smoke_subset.yaml` 提供全离线 smoke 子集
  （评分模式对齐论文 Table 3），fixture bundle
  `evals/fixtures/drb/citation_fixture.json` 携带 `audit_summary.citation_verification`，
  供引用真实性门禁聚合。

### 引用真实性门禁

- 语义映射（常量默认，可由配置覆盖，见 `evals/external/configs/drb_gate.yaml`
  `semantic_mapping`）：`passed=verified`；`failed=unsupported+fetch_failed`；
  `unresolved=unverifiable`。
- `verified_rate = passed / (passed + failed + unresolved)`；
  分母为空时 `verified_rate=None` 判定为 blocked（reason `no_citation_evidence`）。
- 阈值从 `evals/external/configs/drb_gate.yaml` 读取（默认 `min_verified_rate: 0.9`），
  脚本不硬编码；低于阈值 CI job `drb-gate` 失败（非零退出码）；smoke 未真正完成
  （blocked/failed）同样判定失败（reason `smoke_run_not_completed`）。
- 基线可复现：提交的 `evals/reports/drb_gate/scorecard.json` 由
  `DRB_GATE_FIXED_TIMESTAMP=2026-08-15T00:00:00+00:00 uv run python scripts/run_drb_gate.py`
  生成（scorecard 不含临时路径；设置该环境变量可字节级复现基线）。

## 人工抽检通道（eval human-sample）

量规：`evals/rubrics/citation_authenticity.yaml`（DRB-II 式 5 级锚点，
维度 = citation_authenticity 引用真伪 / verbatim_consistency verbatim 一致性 /
source_quality 来源质量 / coverage 覆盖面）。语义映射与门禁一致：
`passed=verified`；`failed=unsupported+fetch_failed`；`unresolved=unverifiable`
（以 YAML 内 `numeric_anchor_guidance` 作为评分锚点，不导入 `scripts/`）。

采样（确定性）：`--bundle-dir` 内所有 `report_bundle.json`（含一层子目录）排序后，
对每个 bundle 用独立 `random.Random(seed)` 抽取 `min(sample_size, 声明数)` 条声明
（按 claim_id 排序），生成评审单；同 seed+同输入 → 逐字节一致。

```bash
# 生成评审单（输出 evals/reports/human_review/<job>.md）
uv run python main.py eval human-sample --bundle-dir evals/fixtures/runs --seed 0 --sample-size 3

# 导入评分并生成 scorecard
uv run python main.py eval human-sample --bundle-dir evals/fixtures/runs \
  --import evals/reports/human_review/demo-anthropic-20260809.scores.yaml
```

评分文件格式（YAML，`job` 缺省时取文件名 stem；维度必须与量规完全一致，
分数为 1–5 整数，按文件名去重、多次导入聚合）：

```yaml
job: demo-anthropic-20260809
dimensions:
  citation_authenticity: 4
  verbatim_consistency: 5
  source_quality: 4
  coverage: 3
```

scorecard（`<job>.scorecard.json`）：per-dimension mean/min/max/count + overall；
`verified_rate` 取自 bundle `audit_summary.citation_verification.summary`
（`passed/(passed+failed+unresolved)`），缺失时 `null` 并附 note。已提交的 fixture
bundle 早于 citation_verification，故 `evals/reports/human_review/*.scorecard.json`
的 `verified_rate` 为 `null`（含 note）；非空路径由测试中的 v2 fixture 覆盖。
安全边界：bundle 读取全部 resolve 于 `--bundle-dir` 内（符号链接逃逸即拒绝）；
评分文件仅作 `yaml.safe_load` 数据解析，无网络、无 exec。

## Head-to-Head 常态化 A/B（head_to_head）

注册名 `head_to_head`（已加入 `BENCHMARK_NAMES`，`main.py benchmark run --benchmark head_to_head`
自动暴露；registry 的 `get_benchmark_descriptor` / `load_benchmark_runner` 均可用）。
适配器 `src/deep_research_agent/evals/external/head_to_head.py` 遵循
`run_benchmark(*, request, descriptor)` 模式：

- **runner 注入**：`baseline_runner=` / `alternative_runner=` 关键字参数（测试用确定性
  fake）；生产用配置 `runner_a` / `runner_b`（模块路径，模块暴露
  `run_pipeline(task) -> str`）。内置生产 runner：`v1_orchestrator_runner`
  （legacy orchestrator-v1，离线确定性、无需凭据）与 `scheduler_v2_runner`
  （scheduler-v2 真实管线）。未配置 runner 或任务集时输出 blocked + 原因。
- **任务集与评分**：配置 `task_spec_path` 指向 JSON `{"tasks": [...]}`（字段对齐
  `BenchmarkTaskSpec`）；评分复用 DRB 的 binary/recall/f1/difference 模式，
  离线确定性，无 judge LLM、无网络、无凭据。
- **产出**：标准 benchmark artifact 集（manifest/official_scores/task_results，
  每个任务 A/B 两行，`official_metrics.runner` 标记边）+ 标准化 scorecard
  `head_to_head_scorecard.json`（per-task 的 score_a/score_b/delta，聚合
  `score_a_mean/score_b_mean/delta_mean/wins/winner_by_metric`）。

```bash
# 配置示例（task_spec_path 指向用户的任务集 manifest）
uv run python main.py benchmark run --benchmark head_to_head \
  --config evals/external/configs/head_to_head.yaml \
  --output-root evals/reports/head_to_head

# 代码直调（可注入 runner，测试与临时对比用）
uv run python -c "
from deep_research_agent.evals.external.contracts import BenchmarkRunRequest
from deep_research_agent.evals.external.head_to_head import run_benchmark
from deep_research_agent.evals.external.registry import get_benchmark_descriptor
request = BenchmarkRunRequest(benchmark_name='head_to_head', output_root='evals/reports/head_to_head')
run_benchmark(request=request, descriptor=get_benchmark_descriptor('head_to_head'),
              baseline_runner=my_runner_a, alternative_runner=my_runner_b)
"
```

**节奏（cadence）**：每轮发布评审前（月度）在离线 smoke 任务集上跑一次 A/B，
基线固定为 v1_orchestrator_runner，对照为候选管线/模型 runner；产出落
`evals/reports/head_to_head/` 并随发布文档附 scorecard 摘要。
