# PLANS.md

## 可信深度研究 App：阶段执行总计划

本文件是当前 release train 的总调度文档。它不描述当前代码“已经是什么”，而描述“接下来按什么边界迁移、按什么阶段验收”。

## 路线结论

采用**抽取可信研究核心 + 阶段性重建产品骨架**的混合路线：

- 保留当前仓库中的可迁移资产
- 不把当前多智能体图继续当成未来产品架构
- 先固化对象合同、治理和评测协议，再服务化、连接器化、审计化

## 当前 active phase

- `Phase 05 — Evidence-First Report Delivery`
- 当前执行入口文档：`specs/phase-05-report-delivery.md`

## 产品目标

最小产品定义：

- 一个异步、可审计、证据优先的深度研究服务
- 用户输入问题，可附带文件和来源约束
- 系统运行分钟级研究任务
- 输出带 claim-level 证据锚点、冲突/不确定性说明、来源与执行轨迹的报告包
- 产物可复查、可导出、可复用

## 非目标

- 不做更复杂的通用聊天产品
- 不做全能 connector 市场
- 不做高权限自动写回外部系统 agent
- 不做“漂亮但不可审计”的前端先行
- 不把 benchmark 分数、报告长度、引用数量当作 ship criteria

## 核心架构决策

### D1. 顶层边界

顶层边界从“谁在说话”改为“哪些对象被生产、验证、编排、治理”：

- `gateway`
- `research_jobs`
- `connectors`
- `evidence_store`
- `auditor`
- `reporting`
- `policy`
- `evals`

### D2. 运行时模型

- 使用确定性状态机驱动 job 生命周期
- LLM 参与 planning、synthesis、audit assistance
- LLM 不拥有整个 job lifecycle

### D3. 核心可信对象

可信研究的核心对象至少包括：

- `ResearchJob`
- `PlanStep`
- `SourceDocument`
- `SourceSnapshot`
- `EvidenceFragment`
- `Claim`
- `ClaimSupportEdge`
- `ConflictSet`
- `AuditEvent`
- `ReportBundle`

### D4. 连接器抽象

统一使用 `search / fetch / file-ingest` 抽象，不接受 ad hoc 工具接入。

### D5. 旧系统定位

- 当前 LangGraph 多智能体流程是 `legacy runtime`
- 旧 benchmark / comparator 是 `migration diagnostics`
- 现有 CLI 是 `developer/debug client`

## Phase 顺序

| Phase | 目标 | 完成标志 |
|---|---|---|
| Phase 01 | 固化可信研究核心合同，隔离 legacy 边界 | 一条真实 run 能产出合法 `report_bundle.json` |
| Phase 02 | 建立可恢复、可取消、可查询状态的 job runtime | CLI 不再直接持有研究主循环 |
| Phase 03 | 统一 connector substrate、snapshot 与 source policy | 核心来源全部走统一 search/fetch 路径 |
| Phase 04 | 建立 claim-level audit pipeline | 关键结论无 evidence edge 不能过 gate |
| Phase 05 | 交付 evidence-first report bundle | 用户无需看内部日志也能审计关键结论 |
| Phase 06 | 用新的 trust eval protocol 取代旧 benchmark 发布门槛 | 发布不再接受旧 report-shape 指标单独过关 |

## Phase 摘要

### Phase 01 — Trust Core Contracts and Legacy Isolation

- 目标：写死 job、snapshot、evidence、claim、audit、bundle 的最小合同
- 产物：phase spec、ADR、migration map、schemas、最小 trace/bundle 输出路径
- 边界：不做 HTTP API，不做 UI，不扩 connector，不重写 prompts

### Phase 02 — Resumable Research Job Orchestrator

- 目标：把本地一次性执行改成可恢复、可取消、可查询状态的 job runtime
- 产物：`research_jobs` 服务层、checkpoint store、event log、status/query interface、thin CLI

### Phase 03 — Connector Substrate, Snapshotting, and Source Policy

- 目标：统一 open web、files、GitHub、arXiv 的 search/fetch/file-ingest 抽象
- 产物：connector contract、snapshot store、source profiles、policy enforcement

### Phase 04 — Claim-Level Audit Pipeline

- 目标：把 claim support、冲突处理和不确定性表达变成硬门槛
- 产物：`auditor/`、claim graph、support edges、critical claim gating、manual review protocol

### Phase 05 — Evidence-First Report Delivery

- 目标：交付物从长文本升级为可展开、可导出、可复核的研究报告包
- 产物：report compiler、evidence expansion、conflict/uncertainty sections、bundle exports

### Phase 06 — Trust Evaluation Platform and Release Gates

- 目标：用新的评测协议替代旧 benchmark 作为发布门槛
- 产物：`evals/` 新协议、rubrics、adversarial suite、release checklist

## 当前仓库资产处理原则

### 保留

- `tools/web_search.py`、`tools/github_search.py`、`tools/arxiv_search.py`
- `main.py` 作为开发/调试客户端
- benchmark fixtures、历史任务样本、workspace 产物
- 现有 tests / ruff / pytest 文化

### 重构

- `research_policy.py`
- `agents/researcher.py`
- `agents/verifier.py`
- `evaluation/metrics.py`
- `memory/evidence_store.py`

### 降级或淘汰

- 多 agent 图作为产品架构真相
- 以 report length / section count / keyword hit 为主的核心指标
- deterministic repair 驱动的 benchmark 美化逻辑
- “竞品没跑通所以我们赢了”的 comparator 叙事

## 文档职责边界

- `AGENTS.md`：长期约束、行为边界、definition of done
- `PLANS.md`：当前 release train 的总计划与 phase 顺序
- `specs/evaluation-protocol.md`：长期评测协议
- `specs/phase-*.md`：阶段性可执行文档
- `docs/adr/adr-*.md`：关键架构决策记录
- `legacy/*.md`：旧 runtime、旧 benchmark、旧模块与新体系的映射

## Open Questions

- 早期持久层最终选型：Postgres JSONB、对象存储 + 索引，还是图存储
- `Claim` 的最小粒度：句子级、atomic claim，还是 hybrid critical-claim 策略
- Phase 03 之后优先接哪类私有 connector
- 第一版产品是否暴露计划审批，还是只做 clarifying + visible plan
- 报告交付先以 HTML viewer 为主，还是 Markdown-first

这些问题不阻塞 Phase 05；当前已完成 phase1/phase2/phase3/phase4，分别覆盖对象模型、legacy 隔离、bundle 落地、job runtime 可恢复性、connector substrate + source policy，以及 claim-level audit pipeline。
