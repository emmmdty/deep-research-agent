# Native Benchmark 使用手册（简体中文）

本文面向没有参与实现的 reviewer、面试官、以及后续接手工程师。目标不是解释所有内部细节，而是让你能快速回答三类问题：

1. 这个 native benchmark 到底在证明什么？
2. 我应该跑哪个命令，产物在哪里看？
3. 这一次 `industry12` benchmark hardening 实际改了什么？

## 1. 先记住两个层次

### `smoke_local` 是什么

`smoke_local` 是当前仓库的权威 release gate。它是小规模、低成本、完全本地、完全可复现的验证层。

它主要回答：

- 现在这条主执行路径还能不能跑通？
- report bundle、claim audit、source policy、file ingest、recovery 这些关键能力有没有退化？
- 当前 `main` 是否仍然满足“可合并、可演示、可复现”的最低证明标准？

权威入口：

- `evals/reports/phase5_local_smoke/release_manifest.json`

### `regression_local` 是什么

`regression_local` 是更宽的 deterministic regression 层。它不替代 release gate，而是扩展 reviewer 可以检查的 native benchmark 覆盖面。

它主要回答：

- `company12` / `industry12` / `trusted8` / `file8` / `recovery6` 这些 suite 在更大任务集上是否仍然稳定？
- reviewer-facing scorecard、casebook、before/after artifacts 是否可以从 repo-local fixtures 重新生成？
- 某一类 benchmark 是否“太容易了”，以至于虽然分数全满，但已经失去鉴别力？

核心产物：

- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`

## 2. 为什么 `smoke_local` 仍然是 release gate

原因很简单：它是最小、最稳定、最适合每次合并前重跑的证明集。

`regression_local` 很有价值，但它的定位是“更宽的 deterministic review surface”，不是“每次合并都必须依赖的唯一真相”。这次优化循环也没有改变这个规则。

可以把它理解成：

- `smoke_local`: merge-safe gate
- `regression_local`: richer local regression evidence

如果两个层都通过，最好。
如果只能先看一个，先看 `smoke_local`。

## 3. 如何重跑

### 重跑 release smoke

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py \
  --output-root evals/reports/phase5_local_smoke \
  --json
```

### 单独重跑一个 smoke suite

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run \
  --suite industry12 \
  --variant smoke_local \
  --output-root /tmp/native_manual/industry12_smoke \
  --json
```

### 重跑完整 native regression

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_native_regression.py \
  --output-root evals/reports/native_regression \
  --json
```

### 单独重跑一个 regression suite

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run \
  --suite industry12 \
  --variant regression_local \
  --output-root /tmp/native_manual/industry12_regression \
  --json
```

### 重建 reviewer-facing native docs

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_native_benchmark_summary.py \
  --reports-root evals/reports/native_regression \
  --docs-root docs/benchmarks/native \
  --json
```

### 重建本轮优化对比产物

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_native_optimization_summary.py \
  --baseline-tag v0.2.0-native-regression \
  --reports-root evals/reports/native_regression \
  --output-root evals/reports/native_optimization \
  --json
```

## 4. 各类产物怎么看

### `report.md`

这是给人读的 markdown 报告。先用它理解任务的结论、措辞、有没有显式写出 uncertainty/conflict。

适合回答：

- 这条 case 在说什么？
- 它有没有“把不确定性说出来”？
- 它有没有把冲突/边界条件写清楚？

### `report_bundle.json`

这是权威机器产物。你要判断 benchmark 是否真的触发了 claim-level auditing、conflict-aware behavior、evidence-first output，优先看这个。

重点字段：

- `claims`
- `claim_support_edges`
- `conflict_sets`
- `audit_summary`
- `sources`
- `snapshots`

### `claim_graph.json`

这是更聚焦的 audit 视角。它把 `claims`、`claim_support_edges`、`conflict_sets` 摘出来，适合快速审阅 claim-level grounding 结构。

### `trace.jsonl`

这是 runtime / stage / bundle emission 的可追踪日志。想确认流程有没有按 deterministic stages 运行、bundle 什么时候输出、事件序列是否稳定，就看这个。

## 5. 如何读 `release_manifest.json`

文件：

- `evals/reports/phase5_local_smoke/release_manifest.json`

建议阅读顺序：

1. `release_gate.status`
2. `suite_order`
3. `suites.<suite_name>.status`
4. `release_gate.categories`

如果你只想快速判断“这次 merge-safe gate 过没过”，看：

- `release_gate.status == "passed"`

如果你想看为什么通过，看 `release_gate.categories` 下面每个 required check 的 `status` 与 `description`。

## 6. 如何读 `native_summary.json`

文件：

- `evals/reports/native_regression/native_summary.json`

建议重点看：

1. `suite_matrix`
2. `casebook.selected_cases`
3. `latest_optimization_cycle`

其中：

- `suite_matrix` 说明每个 suite 的 `smoke_local` / `regression_local` task count、status、purpose
- `casebook.selected_cases` 告诉你 reviewer 最值得直接打开哪几个 case
- `latest_optimization_cycle` 说明最近一次 benchmark hardening 的方向，以及它没有改变 release gate 规则

## 7. 如何读本轮 `optimization_summary.json`

文件：

- `evals/reports/native_optimization/optimization_summary.json`

这是本轮优化循环最重要的机器摘要。

建议阅读顺序：

1. `baseline_commit`
2. `baseline_tag`
3. `selected_target`
4. `baseline_metrics`
5. `post_change_metrics`
6. `deltas`
7. `interpretation`

本轮应该重点看到这些 delta：

- `industry12_conflict_case_count: 0 -> 4`
- `industry12_multi_claim_task_count: 0 -> 4`
- `industry12_uncertainty_case_count: 0 -> 4`
- `industry12_casebook_conflict_example_present: false -> true`
- `industry12_suite_status` 仍为 `passed`
- `industry12_task_count` 仍为 `12`

如果你更喜欢人类可读版，可以直接看：

- `evals/reports/native_optimization/BEFORE_AFTER.md`

## 8. 本轮 `industry12` hardening 改了什么

这次没有去优化 runtime，也没有去做 provider-backed full native run。

只做了一件事：把 `industry12` 里最缺乏鉴别力的 4 个 regression case 加固成真正会触发 conflict / uncertainty / multi-claim 语义的 deterministic fixtures。

被加固的任务是：

- `industry-model-gateway`
- `industry-eval-grounding`
- `industry-observability`
- `industry-governance-policy`

统一改动方式：

- 每个任务显式写出至少 2 条 `claims`
- 每个任务显式写出 `claim_support_edges`
- 每个任务显式写出非空 `conflict_sets`
- 每个任务至少保留 1 条 `medium` 或 `high` uncertainty claim
- `report.md` 不再只写“全部成立”，而是显式承认冲突或边界不确定性

所以这次优化的本质不是“分数更高”，而是“benchmark 更难、更像真实 reviewer 关心的问题”。

## 9. 推荐 reviewer 的最短检查路径

如果你只有 5 分钟：

1. 看 `evals/reports/phase5_local_smoke/release_manifest.json`
2. 看 `docs/benchmarks/native/NATIVE_SCORECARD.md`
3. 看 `docs/benchmarks/native/CASEBOOK.md`
4. 看 `evals/reports/native_optimization/BEFORE_AFTER.md`
5. 打开 `industry-governance-policy` 的 `report.md` 与 `bundle/report_bundle.json`

如果你只有 1 分钟：

1. 确认 `smoke_local` 仍是 `passed`
2. 确认 `optimization_summary.json` 里三个核心计数都从 `0 -> 4`

## 10. 仍未覆盖的边界

这套 native benchmark 仍然有明确边界，不应过度解读：

- 不是 provider-backed full native execution
- 不覆盖 live web freshness
- 不覆盖 blind/private external benchmark submission
- 不覆盖多租户部署、auth、远程队列、对象存储
- 不等于真实线上成本/延迟画像

因此它最适合做：

- 本地可复现 regression
- reviewer-facing evidence
- 面试时解释“这个仓库到底证明了什么”

它不适合被描述成：

- 线上生产压测结果
- 全量外部 benchmark 成绩单
- provider 真机对比结论
