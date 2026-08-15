# 「移除结构」季度评审记录（Evaluation Review）

> 状态：2026-08 首轮（first edition）。对齐 OPTIMIZATION_PLAN §6 四期条目 16：按 bitter lesson，
> 随模型能力提升每季度重新审视哪些外围编排结构该拆。**证据契约（claim graph / audit gate /
> review queue）是本项目相对竞品的差异点（OPTIMIZATION_PLAN §7），永不列入候选**；harness
> 层面由保护规则强制拒绝。
> 本文件是可审计产物：所有结论由提交的 harness 输出复现（`tests/test_ablation_removal.py`
> 的 `test_committed_scorecard_matches_recomputation` 直接重算比对提交产物，见 §4）。

## 1. 可拆 / 不可拆清单

### 1.1 不可拆：证据契约（PROTECTED，harness 强制拒绝）

| 结构 | 模块路径 | 理由 |
| --- | --- | --- |
| claim graph | `src/deep_research_agent/auditor/`（models/store） | claim 图是"错误可被证明"的落地点：claims/edges/conflicts 的落盘与一致性，任何拆除都让引用无法回查 |
| audit gate | `auditor/pipeline.py`、`auditor/models.py` | 审计门禁阻止未支撑的 critical claim 出报告；降级 = 回到"模型自述"时代，违反证据优先定位 |
| review queue | `auditor/store.py`、`research_jobs/{store,service}.py` | 人工复核队列是"无法证明的内容进入人工面"的通道，是证据契约的闭环 |

保护规则（harness 常量，`evals/ablation_removal.py`）：移除定义 id 命中 `PROTECTED_IDS`，
或模块路径命中 `deep_research_agent/auditor/`，或 id/描述/路径引用 claim graph / audit gate /
review queue 语义关键词 → `ProtectedStructureError` 拒绝注册与 override。

曾考虑但被保护规则拒绝的候选：**verbatim span matcher**（`auditor/span_matcher.py`）——它看似
"外围"匹配机制，但实现 quote containment 程序化校验（二期条目 5），位于证据契约目录内，
**不可拆**。这是本轮的实证发现：看名字像外围、看归属是契约。

### 1.2 可拆候选（证据契约之外的外围编排结构，harness 注册表）

| 结构 | 模块路径 | removable_in_ci | 本轮判定 | 备注 |
| --- | --- | --- | --- | --- |
| semantic_rerank | `retrieval/rerank.py` | ✅ | removable_now（待 2026-11 复核） | 唯一可拆候选，但受 fixture 尺度限制（见 §2） |
| parallel_fetch_concurrency | `agents/researcher.py` | ✅ | keep | 有界并发，同时是成本结构 |
| agentic_coverage_assessment | `agents/researcher.py`、`agents/planner.py` | ✅ | keep | 覆盖率自评低成本高收益 |
| executive_summary_dual_track | `reporting/bundle_v2.py` | ✅ | keep | 模型原文保留的兜底 |
| cheap_model_summarization | `providers/router.py` | ✅ | keep | 成本结构，2026-11 结合真实成本复核 |
| distributed_job_queue | `research_jobs/store.py` | ❌（未落地） | needs_review（doc-only） | 三期条目 12 延后；替换会触碰与 review_queue_path 同文件的列，需单独评审 |

### 1.3 评审原则（bitter lesson framing）

- 结构存在 ≠ 结构必要。模型能力每季度都在变（RL 训练研究代理、原生 browsing），
  当年为弥补模型弱点的编排结构（确定性兜底、双轨、预算、路由）在模型更强时可能变成纯成本。
- 反方向同样成立：不要为"简化"拆除有可测量收益的结构；判定依据是 harness 的确定性测量 +
  语义理由，不是印象。
- 拆的是**外围编排**，守的是**证据契约**。契约从 2026-08 起由 harness 保护规则强制兜底，
  不依赖评审人记忆。
- 测量尺度诚实声明：本轮为 smoke 尺度（单任务 fixture），判定的是"该 fixture 上可测量到的
  影响"，不是全量收益；每季度换更大 fixture 与真实成本测量后再做拆除决定。

## 2. 本轮消融结果（2026-08）

提交的 harness 输出（本文件的数字均取自该产物）：

- `evals/reports/ablation_removal/quarterly_2026_08_ablation_scorecard.json`
  （run_id `ablation-removal-2026-08`，离线确定性测量 v1，无 LLM/网络）

测量 fixture（只读）：`evals/suites/company12.yaml` → `evals/datasets/company12.smoke.yaml`
（1 task / 2 sources）。指标：citation_resolvable_rate、question_coverage、summary_retention、
source_rank_quality，综合分 = 四者均值。判定规则：Δ≤0 → removable_now；0<Δ≤0.1 → needs_review；
Δ>0.1 → keep（Δ = with − without，>0 表示移除有损）。

| 结构 | with | without | Δ | 判定 |
| --- | ---: | ---: | ---: | --- |
| semantic_rerank | 1.0 | 1.0 | 0.0 | removable_now |
| parallel_fetch_concurrency | 1.0 | 0.875 | 0.125 | keep |
| agentic_coverage_assessment | 1.0 | 0.875 | 0.125 | keep |
| executive_summary_dual_track | 1.0 | 0.75 | 0.25 | keep |
| cheap_model_summarization | 1.0 | 0.875 | 0.125 | keep |
| distributed_job_queue | — | — | — | needs_review（doc-only，未落地） |

要点：

- 唯一 removable_now 是 **semantic_rerank**：smoke fixture 下报告引用顺序与相关性排序一致，
  移除无可测量差异。但这是单任务 fixture 的尺度局限——小 fixture 无差异 ≠ 真实无差异，
  2026-11 换多任务 fixture 复核后才可执行拆除。
- 四个 keep 中最该盯的是 **executive_summary_dual_track**（Δ0.25，摘要保真 1.0→0.0）：
  双轨是二期条目 7"报告保留模型原文"的兜底，拆掉等于退回三期前的确定性重建缺陷。
- **distributed_job_queue** 是 doc-only 条目：队列化尚未落地（三期条目 12 延后单独发布），
  无运行时实现可移除；且其替换会触碰 job 存储中与 review_queue_path 同文件的列，
  与证据契约存储相邻，必须单独评审后再动。
- 被保护规则拒绝的候选 **verbatim_span_matcher**（`auditor/span_matcher.py`）说明：
  保护匹配按"归属"而非"名字"判定——看起来像外围的结构如果住在契约目录里，照样不可拆。

## 3. 季度节奏（quarterly cadence）

| 轮次 | 时间 | 状态 |
| --- | --- | --- |
| 2026-08 | 首轮（本文件 + `quarterly_2026_08_ablation_scorecard.json`） | ✅ 已完成 |
| 2026-11 | 第二轮：多任务 fixture、真实 token 成本测量、semantic_rerank 拆除复核 | ⬜ 待办 |
| 2027-02 | 第三轮 | ⬜ 待办 |
| 2027-05 | 第四轮 | ⬜ 待办 |

节奏规则：每季度一次；同一 fixture 重复测量（排除 run_id/generated_at 后字节一致，
`tests/test_ablation_removal.py::test_scorecard_payload_is_deterministic_except_timestamps`
有断言）保证跨轮可比；每轮更新本文件与对应 scorecard，旧产物保留不删。

## 4. 如何重跑（exact command）

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python evals/ablation_removal.py
```

- 输出：`evals/reports/ablation_removal/quarterly_<period>_ablation_scorecard.json`
  （默认 period `2026-08`，默认 fixture `evals/suites/company12.yaml`）。
- 参数：`--period 2026-11`、`--output-dir <dir>`、`--fixture-suite evals/suites/<suite>.yaml`。
- 确定性：相同提交 fixture → 除 run_id/generated_at 外字节一致。
- 回归：`UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_ablation_removal.py`。
- 可审计性：`test_committed_scorecard_matches_recomputation` 会直接重算提交的 scorecard 并
  断言与提交产物完全相等——本文件的数字因此可复现，不是 prose-only。
