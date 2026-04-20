# Deep Research Agent 架构设计文档

> 本文档描述的是**当前仓库已落地的 runtime 架构事实**，用于帮助维护 legacy 实现。
> 目标产品路线、迁移边界与未来架构决策请看：
> `AGENTS.md`、`PLANS.md`、`specs/phase-*.md`、`docs/adr/adr-*.md`。
> 当前不要把本文档误读为未来产品架构。

## 系统架构

Deep Research Agent 是一个基于 LangGraph 的多智能体深度研究系统，采用 **Supervisor + Verifier** 模式协调多个专业 Agent 完成端到端的研究任务。

phase2 以后，**公开 CLI runtime** 已经切换为 `services/research_jobs/` 下的确定性 job orchestrator：

- `main.py submit/status/watch/cancel/retry` 是当前公开入口
- job 状态、event、checkpoint 存在 `workspace/research_jobs/`
- runtime worker 通过 store 原子获取 `worker_lease_id`；已有活跃 lease 时，新 worker 不会覆盖当前 owner，worker 退出时也只能清理自己的 lease
- event 与 checkpoint 由 store 在写入事务中分配单调 sequence，event log 和 checkpoint metadata 不再依赖调用方预先取号，也不允许静默覆盖既有 sequence
- `cancel` 是幂等请求：已请求取消或已进入终态的 job 不会重复追加 `job.cancel_requested` 事件；`retry` 对同一个直接原 job 采用 create-or-return 语义，避免重复派生 retry job
- phase3 以后，collecting 阶段通过 `connectors/ + policies/ + snapshot store` 统一治理 `search / fetch / file-ingest`
- public connector substrate 在 fetch 前执行 URL 安全检查，显式阻止非 `http(s)`、localhost、loopback/private/link-local 等明显不安全地址；当前尚不包含 DNS 解析或 redirect 复检级 SSRF 防护
- phase4 以后，`extracting` 后新增 `claim_auditing`，公开 runtime 会输出 claim graph、review queue 和 `completed + blocked` 审计门禁结果
- phase6 以后，API readiness 只落在 ADR/spec；当前没有受支持的 HTTP/API server surface
- `workflows/graph.py` 仍保留为 legacy runtime，主要服务 benchmark、comparator 和 hidden `legacy-run`

因此，本文档中的多智能体图描述的是**当前仓库仍然存在的 legacy 工作流事实**，不是公开 CLI 的顶层运行时边界。

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

phase5 以后，`release_manifest.json` 还包含 `release_gate` 字段。该 gate 从 `configs/release_gate.yaml` 读取分层检查项，当前分为 `runtime_reliability`、`connector_security`、`audit_grounding`、`benchmark_diagnostics`、`docs_surface`。`benchmark_diagnostics` 是必需项，但不能单独让 release gate 通过。当前 release gate 是本地 manifest/checklist，不是外部 CI 或生产监控。

为了让 benchmark profile 更稳定，Researcher 在使用 LLM 生成总结后还会执行一次 lightweight validator：

- 若缺少 expected aspects
- 若没有引用
- 若高可信 selected sources 没有被正文使用
- 若 case-study 有官方/一手证据但总结未显式披露来源性质

则回退到 deterministic summary，并把修复次数记录到 `RunMetrics.summary_repair_count`。
### 7. LLM 输出清洗

MiniMax 等模型可能在输出中包含 `<think>` 思维链标签。
`llm/clean.py` 提供统一清洗，所有 Agent 节点在处理 LLM 响应时自动调用。

### 8. Phase 03 connector substrate 与证据模型

phase3 以后，公开 runtime 的 collecting 路径不再直接把搜索候选塞进 `SourceRecord`。统一链路变成：

`capability planning -> connector search -> source policy -> budget guardrails -> fetch/file-ingest -> snapshot store -> SourceRecord`

这意味着：

- `SourceRecord` 代表的是**已抓取文档**，不是搜索结果壳
- `sources_gathered` 中的公开 runtime 文档都必须带 `snapshot_ref`
- domain allow / deny、source profile、per-job fetch budget 会先于 verifier 生效
- legacy `tools/*.py` 仍存在，但在 phase3 公开路径中只通过 adapter 使用

当前公开 runtime 相关组件如下：

| 组件 | 用途 | 主要产物 |
|------|------|----------|
| `connectors/registry.py` | 统一 search / fetch / file-ingest 分发 | `SearchResultItem`、fetched document |
| `policies/source_policy.py` | source profile、domain allow / deny、auth_scope 约束 | 允许 / 拒绝决策 |
| `policies/budget_guardrails.py` | 每 job 抓取预算 | fetch permit / rejection |
| `connectors/snapshot_store.py` | snapshot 持久化、hash、canonical URI | `SourceSnapshot` manifest + raw text |
| `connectors/legacy.py` | 兼容现有 `tools/*.py` | connector adapter |
| `verifier` | 证据聚类、实体一致性、持久化记忆 | `MemoryStats` |
| `writer` | 统一引用编号与参考来源表 | `ReportArtifact` |
| `cost_tracker` | 记录 LLM / 搜索调用 | `RunMetrics` |

核心状态对象包括：
- `SourceRecord`：已抓取文档的标题、canonical URI、`snapshot_ref`、`auth_scope`、freshness metadata
- `EvidenceNote`：每轮研究总结及支撑来源编号
- `source_snapshots`：runtime 中已经落盘的 snapshot manifests
- `EvidenceUnit / EvidenceCluster / VerificationRecord / MemoryStats`
- `RunMetrics`：耗时、LLM 调用、搜索调用、skill/MCP 激活与工具成功率
- `ReportArtifact`：最终报告、引用表、证据表、验证记录与运行指标

### 9. Phase 04 claim-level audit pipeline

phase4 以后，公开 runtime 的可信边界不再停留在 `EvidenceUnit / VerificationRecord`。新增的公开事实是：

- `verifier` 会先产出 `EvidenceFragment`
- `claim_auditing` 会从 `EvidenceNote / task_summaries` 抽取 claim
- claim graph 由以下对象组成：
  - `Claim`
  - `ClaimSupportEdge`，其中 edge 保留 `source_id`、`snapshot_id`、`locator`、`grounding_status`
  - `ConflictSet`
  - `CriticalClaimReviewItem`
- `claim_auditing` 只把 `grounding_status = grounded` 且非 `context_only` 的 edge 作为关键 claim 的支撑或冲突依据
- 缺少 source、snapshot、locator 或 excerpt 的 evidence fragment 不会让关键 claim 通过；关键 claim 会进入 blocked review queue
- 关键 claim 未通过审计时，job 不会伪装成 fully-passed；当前语义是：
  - `status = completed`
  - `audit_gate_status = blocked`
- 当前 relation 判定仍是启发式文本 overlap，不等于完整自动事实核验
- 相关侧车产物位于：
  - `workspace/research_jobs/<job_id>/audit/claim_graph.json`
  - `workspace/research_jobs/<job_id>/audit/review_queue.json`

因此，当前公开 runtime 的阶段事实应理解为：

`clarifying -> planned -> collecting -> extracting -> claim_auditing -> rendering`

## 模块职责

| 模块 | 职责 |
|------|------|
| `agents/` | 6 个 Agent 节点定义（LangGraph node 函数） |
| `services/research_jobs/` | phase2 公开 job runtime、lease、event、checkpoint、worker |
| `connectors/` | phase3 统一 connector substrate、snapshot store、legacy adapters |
| `policies/` | source profiles、domain policy、budget guardrails |
| `capabilities/` | builtin / skill / mcp 注册表、MCP runtime 与适配 |
| `workflows/` | LangGraph 状态图定义 + 状态模型 |
| `tools/` | @tool 装饰器的工具函数 |
| `prompts/` | 系统提示词 + 用户提示词模板 |
| `llm/` | LLM Provider 封装 + 输出清洗 |
| `configs/` | Pydantic BaseSettings 配置管理 |
| `evaluation/` | 评估指标、blind judge、成本追踪、comparator 协议 |
| `memory/` | SQLite 证据记忆与研究笔记持久化 |
| `scripts/` | benchmark runner、local3 优化脚本、full comparison、报告导入与离线对比脚本 |
