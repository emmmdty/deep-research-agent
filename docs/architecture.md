# Deep Research Agent 架构设计文档

## 系统架构

Deep Research Agent 是一个基于 LangGraph 的多智能体深度研究系统，采用 **Supervisor + Verifier** 模式协调多个专业 Agent 完成端到端的研究任务。

## 工作流

```
用户输入研究主题
        │
        ▼
┌──────────────┐
│  Supervisor   │  初始化研究流程
└──────┬───────┘
       ▼
┌──────────────┐
│   Planner     │  拆解主题为 3-5 个子任务（JSON 输出）
└──────┬───────┘
       ▼
┌──────────────┐
│  Researcher   │  能力路由 + 多源搜索 + skill 指导总结
└──────┬───────┘
       ▼
┌──────────────┐
│   Verifier    │  证据聚类、实体一致性、SQLite 记忆
└──────┬───────┘
       ▼
┌──────────────┐
│    Critic     │  评审研究质量（0-10 分）
└──────┬───────┘
       │
       ├── 不满足 → 生成补充查询 → 回到 Researcher（最多 3 轮）
       │
       └── 满足 →
              ▼
       ┌──────────────┐
       │    Writer     │  整合所有总结 → 结构化 Markdown 报告
       └──────┬───────┘
              ▼
         输出报告 + 保存到 workspace
```

## 核心设计决策

### 1. LangGraph TypedDict 状态

使用 `TypedDict + Annotated` 定义状态 schema，并按字段职责指定合并策略：
- 研究循环中的列表字段（`task_summaries`、`sources_gathered`、`search_results`、`evidence_notes`）：**覆盖替换**
- 标量字段（`status`、`loop_count`、`final_report`）：**覆盖替换**

这样可以避免 Critic 触发多轮迭代时，旧来源和旧总结被 LangGraph reducer 重复累计。

### 2. Capability Registry 与 Specialist Routing

Researcher 不再只是“按 enabled_sources 顺序搜索”，而是先根据任务类型和方面覆盖缺口，从 `builtin / skill / mcp` 三类能力中生成任务级 capability plan：

- `builtin`：`web.search`、`github.search`、`arxiv.search`
- `skill`：兼容 Claude Code 风格目录组织，从 `SKILL.md` 读取元数据与策略提示
- `mcp`：从 `stdio / sse / streamable-http` server 配置归一化为统一能力对象，并缓存发现到的工具 schema

benchmark profile 下，教程类主题优先 `web + github + installation skill`，研究类主题优先 `web + arxiv + github`。

### 3. Critic 迭代循环

Critic 通过条件边实现"满足/不满足"路由：
- 不满足时回到 Researcher 执行补充搜索
- benchmark profile 下保留 `quality_gate_status`
- benchmark profile 下若到达最后一轮仍未通过 `quality_gate`，工作流直接进入 `failed_quality_gate` 终态，不再进入 Writer
- `case-study / 行业应用案例` 会触发专门的 product-style 检索策略，并要求至少存在一条 `官方站点 / 一手仓库` 的高可信案例证据
- case-study 任务不是单条泛 query，而是 query bundle：官方域名 `site:` 查询、GitHub 一手仓库查询、产品博客/客户案例查询、失败后的 rescue queries

### 4. Verifier 与证据记忆

Verifier 会把 `SourceRecord + EvidenceNote` 转为结构化证据层：

- `EvidenceUnit`：最小证据单元
- `EvidenceCluster`：跨源聚类
- `VerificationRecord`：任务级验证记录
- `MemoryStats`：高可信比例、冲突数、实体一致性

这些数据通过 `memory/evidence_store.py` 持久化到 `workspace/memory/evidence.db`，用于 benchmark 审计和后续写作约束。

### 5. Scorecard 式 Benchmark 输出

benchmark runner 不再只输出容易落成 `0/1` 的传统字段；当前 summary 会把结果拆成两层：

- `scorecard`：主展示层，输出 `research_reliability_score_100`、`system_controllability_score_100`、`report_quality_score_100`、`evaluation_reproducibility_score_100`
- `legacy_metrics`：兼容层，继续保留 `aspect_coverage`、`citation_accuracy`、`depth_score`、`judge_*` 等字段的聚合结果
- `benchmark_health`：补充输出 `completion_rate_100`、`quality_gate_pass_rate_100`、`judge_status`、恢复韧性等实验健康度信号
- 对 case-study 任务，summary 还会补充 `case_study_strength_score_100`、`first_party_case_coverage_100`、`official_case_ratio_100`、`case_study_gate_margin_100`

这样既能保持历史 benchmark 的兼容性，又能把多源研究的可信度、验证强度、引用对齐和系统控制能力用连续值展示出来。

### 6. Ablation 与作品集研究集

为了把 `Verifier + Quality Gate + Capability Routing` 的方法收益讲清楚，仓库新增两条研究工程入口：

- `portfolio12`：12 题主题集，覆盖 research / comparison / tutorial / product 四类任务
- `scripts/run_ablation.py`：运行 `ours_base / ours_verifier / ours_gate / ours_full` 四个内部变体，用于对照 verifier 与 gate 的增益
- `scripts/run_portfolio12_release.py`：支持 `hybrid / full-live` 两种模式；默认 `hybrid` 会对 `T01,T04,T11` 做 live judge 校准，并产出全量 `portfolio12` 的 benchmark / ablation / `RESULTS.md` / `release_manifest.json`

为了让 benchmark profile 更稳定，Researcher 在使用 LLM 生成总结后还会执行一次 lightweight validator：

- 若缺少 expected aspects
- 若没有引用
- 若高可信 selected sources 没有被正文使用
- 若 case-study 有官方/一手证据但总结未显式披露来源性质

则回退到 deterministic summary，并把修复次数记录到 `RunMetrics.summary_repair_count`。
### 7. LLM 输出清洗

MiniMax 等模型可能在输出中包含 `<think>` 思维链标签。
`llm/clean.py` 提供统一清洗，所有 Agent 节点在处理 LLM 响应时自动调用。

### 8. 多源研究与证据模型

Researcher 不再只拼接单一搜索文本，而是按来源类型收集结构化证据，并在 benchmark profile 下做来源筛选与可信度分层：

| 组件 | 用途 | 主要产物 |
|------|------|----------|
| `web_search` | 通用网页搜索 | `SourceRecord(source_type="web")` |
| `github_search` | GitHub 仓库/代码线索 | `SourceRecord(source_type="github")` |
| `arxiv_search` | 论文搜索 | `SourceRecord(source_type="arxiv")` |
| `verifier` | 证据聚类、实体一致性、持久化记忆 | `MemoryStats` |
| `writer` | 统一引用编号与参考来源表 | `ReportArtifact` |
| `cost_tracker` | 记录 LLM / 搜索调用 | `RunMetrics` |

核心状态对象包括：
- `SourceRecord`：标题、URL、来源类型、查询、可信度与筛选结果
- `EvidenceNote`：每轮研究总结及支撑来源编号
- `EvidenceUnit / EvidenceCluster / VerificationRecord / MemoryStats`
- `RunMetrics`：耗时、LLM 调用、搜索调用、skill/MCP 激活与工具成功率
- `ReportArtifact`：最终报告、引用表、证据表、验证记录与运行指标

## 模块职责

| 模块 | 职责 |
|------|------|
| `agents/` | 6 个 Agent 节点定义（LangGraph node 函数） |
| `capabilities/` | builtin / skill / mcp 注册表、MCP runtime 与适配 |
| `workflows/` | LangGraph 状态图定义 + 状态模型 |
| `tools/` | @tool 装饰器的工具函数 |
| `prompts/` | 系统提示词 + 用户提示词模板 |
| `llm/` | LLM Provider 封装 + 输出清洗 |
| `configs/` | Pydantic BaseSettings 配置管理 |
| `evaluation/` | 评估指标、blind judge、成本追踪、comparator 协议 |
| `memory/` | SQLite 证据记忆与研究笔记持久化 |
| `scripts/` | benchmark runner、local3 优化脚本、full comparison、报告导入与离线对比脚本 |
