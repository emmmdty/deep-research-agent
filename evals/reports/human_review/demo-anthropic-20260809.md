# 人工抽检评审 — demo-anthropic-20260809

> 量规：`evals/rubrics/citation_authenticity.yaml`（DRB-II 风格，1–5 级锚点，2/4 为相邻锚点之间）
> 采样：seed=0，sample_size=3，bundle=evals/fixtures/runs/demo-anthropic/report_bundle.json

## 评分区（按量规 4 个维度打分，整数 1–5）

| 维度 | 说明 | 评分 |
|---|---|---|
| `citation_authenticity`（引用真伪） | 引用是否真实对应来源文本，声明是否得到来源支持（passed=verified；failed=unsupported+fetch_failed；unresolved=unverifiable）。 | ____ |
| `verbatim_consistency`（verbatim 一致性） | 引用摘录与来源原文是否逐字一致，无改写、拼接或断章取义。 | ____ |
| `source_quality`（来源质量） | 来源的权威性、时效性与相关性（官方文档、一手数据优于聚合页/自媒体）。 | ____ |
| `coverage`（覆盖面） | 报告关键方面是否被声明与来源覆盖，抽检声明是否覆盖报告主要结论。 | ____ |

## 抽检声明

| # | claim_id | critical | 声明 | 来源 URL | 原文摘录 |
|---|---|---|---|---|---|
| 1 | claim-1 | 是 | Anthropic 由 Dario Amodei 与 Daniela Amodei 于 2021 年创立，核心成员多来自 OpenAI，公司定位为 AI 安全与前沿研究机构。 | https://www.anthropic.com/about | Anthropic is an AI safety and research company founded in 2021 by Dario Amodei and Daniela Amodei, with core members coming from OpenAI. |
| 2 | claim-11 | 是 | Anthropic 2025 年上半年确认与政府部门在国防与情报领域的合作传闻（具体合同细节无法核实）。 | （无证据引用） | （无原文摘录） |
| 3 | claim-7 | 是 | Anthropic 多 agent 系统采用 orchestrator-workers 模式：主 agent 将研究主题拆分为并行子任务，子 agent 独立上下文并行检索，并将结果写入文件系统以规避上下文丢失。 | https://www.anthropic.com/engineering/built-multi-agent-research-system | Lead agent delegates research topics to parallel sub-agents; sub-agents write findings to the filesystem to avoid context loss. |

## Bundle 审计摘要

- status: `completed`
- gate_status: `passed`
- citation_verification.summary: （缺失）
- 语义映射：passed=verified；failed=unsupported+fetch_failed；unresolved=unverifiable

## 量规锚点（评审参考）

### citation_authenticity（引用真伪）
- 1 分：多数抽检引用的语义判定为 failed（unsupported 或 fetch_failed），或 verified_rate 低于 0.5。
- 3 分：抽检引用大部分为 passed（verified），存在少量 unresolved（unverifiable），且无 failed。
- 5 分：抽检引用全部为 passed（verified），声明逐条对应来源文本，无 failed/unresolved。

### verbatim_consistency（verbatim 一致性）
- 1 分：多数引用摘录与来源原文不一致（改写、错引、拼接），关键声明无法回溯到原文片段。
- 3 分：引用摘录与来源原文基本一致，仅个别标点/空白差异，无实质改动。
- 5 分：所有引用摘录与来源原文逐字一致，quote 可从来源文本精确回溯。

### source_quality（来源质量）
- 1 分：多数来源为低质聚合页/自媒体/无关页面，或来源无法获取（fetch_failed）。
- 3 分：来源以一手或二手资料为主，存在少量聚合页/低信源，但不影响核心声明。
- 5 分：全部来源为权威一手资料（官方文档/年报/一手数据），时效与主题高度相关。

### coverage（覆盖面）
- 1 分：报告大量关键方面无任何声明/来源覆盖，抽检声明集中于单一主题。
- 3 分：报告主要方面均有声明覆盖，个别次要方面缺失。
- 5 分：报告所有关键方面均有声明与来源覆盖，抽检声明均匀覆盖各主要结论。
