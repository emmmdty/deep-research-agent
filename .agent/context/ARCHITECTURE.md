# 7. 目标架构设计

## 7.1 顶层模块边界

1. **gateway**
   CLI、HTTP API、batch API、artifact API、review API。

2. **research_jobs**
   job service、state machine、worker、leases、events、checkpoints、stage executors。

3. **connectors**
   web/github/arxiv/files/mcp_bridge，各自 search/fetch/ingest 实现。

4. **policy**
   source profiles、trust taxonomy、budget guardrails、fetch validation。

5. **evidence_store**
   document normalization、snapshots、chunks、evidence fragments、claims、edges、conflicts。

6. **auditor**
   claim audit pipeline、gate、review queue、override log。

7. **reporting**
   report compiler、bundle schema、HTML viewer contract、export。

8. **providers**
   OpenAI / Anthropic / compatible adapters、router、capability registry、call ledger。

9. **retrieval**
   query rewrite、embedding、rerank、dedupe、source diversification。

10. **observability**
    tracing、metrics、structured logs。

11. **evals**
    datasets、rubrics、graders、suite runners、release gate。

## 7.2 关键对象合同

| 对象                 | 最关键字段                                                                                      | 说明           |
| ------------------ | ------------------------------------------------------------------------------------------ | ------------ |
| `ResearchJob`      | `job_id, brief, status, audit_gate_status, source_profile, attempt, artifact_manifest_ref` | 生命周期真相       |
| `PlanStep`         | `step_id, step_type, question_refs, budget_slice, exit_criteria`                           | 研究计划最小单元     |
| `SourceDocument`   | `document_id, canonical_uri, auth_scope, connector_name, snapshot_ref`                     | 统一来源对象       |
| `SourceSnapshot`   | `snapshot_ref, content_hash, fetched_at, raw_ref, text_ref, manifest`                      | 证据留痕         |
| `EvidenceFragment` | `evidence_id, snapshot_ref, locator, excerpt, confidence`                                  | claim 支撑最小单位 |
| `Claim`            | `claim_id, claim_type, criticality, text, status, uncertainty`                             | 关键结论对象       |
| `ClaimSupportEdge` | `edge_id, claim_id, evidence_id, relation, confidence`                                     | 支撑/冲突关系      |
| `ConflictSet`      | `conflict_id, claim_ids, evidence_ids, summary`                                            | 冲突聚合对象       |
| `AuditDecision`    | `gate_status, blocking_claim_ids, summary, review_queue_ref`                               | 审计结论         |
| `ReportBundle`     | `manifest, findings, claims, sources, audit_summary, artifacts`                            | 交付真相         |

## 7.3 关键服务与职责

* `JobService`：创建 job、状态查询、事件流、取消/重试/恢复/细化
* `StateMachine`：唯一合法状态迁移
* `StageExecutor`：planning / collecting / normalizing / extracting / auditing / synthesizing / rendering
* `ConnectorRegistry`：根据 profile 与 task 选择 connector
* `SnapshotService`：写 snapshot、去重、计算 hash、读取 manifest
* `EvidenceLinker`：从 chunks 生成 fragments，并建立 claim-support edges
* `AuditService`：运行 gate、生成 review queue
* `ReportCompiler`：把 claims/evidence/uncertainty 编译成 bundle 与 viewer artifacts
* `ProviderRouter`：按 capability / cost / availability 路由模型
* `EvalRunner`：离线/在线评测与 release gate

## 7.4 Runtime 生命周期

建议生命周期：

`created -> clarifying -> planned -> collecting -> normalizing -> extracting -> claim_auditing -> synthesizing -> rendering -> completed`

旁路事件：

* `cancel_requested -> cancelled`
* `failed -> retry_of(new_job)`
* `claim_auditing(blocked)`：

  * 若仍有循环预算：回到 `collecting`
  * 否则：执行完成，但 `audit_gate_status=blocked`，进入 review queue

## 7.5 request -> plan -> collect -> extract -> audit -> synthesize -> render -> deliver 全链路

**request**
API/CLI 接收 brief，写入 `ResearchJob`，附 source profile、budget、file inputs。

**plan**
planner 产出 `QuestionSet + PlanSteps`，validator 检查覆盖率与策略一致性。

**collect**
connector registry 按 step 与 policy 发起 search / fetch / ingest；每个 document 必须 snapshot。

**extract**
normalizer/chunker 生成标准化文档；extractor 提取 evidence fragments；claim builder 生成 claims。

**audit**
support linker 建边；conflict detector 聚合冲突；gate 判定是否 block。

**synthesize**
在 audit 结果约束下生成 findings、comparisons、unknowns、recommendations。

**render**
输出 Markdown / HTML / JSON bundle / PDF。

**deliver**
用户通过 API/CLI 获取 artifact URLs、event stream、review queue。

## 7.6 API / CLI / worker / store / eval / reporting 关系

* CLI 和 API 都只是 gateway
* worker 只通过 `JobService + StateMachine` 驱动 job
* store 不允许被 stage executor 直接乱写，必须经 repository/service
* reporting 不直接调用 connector；它只消费 bundle-ready objects
* evals 不直接调用旧 scripts；它调用正式 API 或正式 runner
* legacy graph 不允许直接成为对外 contract

## 7.7 哪些部分 deterministic，哪些部分是 LLM-assisted

**Deterministic**

* 状态迁移
* source policy
* allow/deny domain
* budget ledger
* snapshot 存储
* URI safety
* event log / checkpoint
* artifact manifest
* release gate 规则
* review override 记录

**LLM-assisted**

* 问题分解
* query expansion
* evidence fragment 抽取候选
* claim 归一化
* conflict characterization
* synthesis / report wording
* readability / rubric 辅助 judge

## 7.8 为什么这个边界比“把所有东西都塞进 agent loop”更可靠

因为企业级研究系统失败的主因，通常不是“不会写总结”，而是：

* 不能恢复
* 不知道用了什么来源
* 不能限制来源
* 不能解释关键结论凭什么成立
* 不能把 blocked 结果暴露给用户
* 不能系统评测

把这些职责全塞进 agent loop，会让 lifecycle、policy、audit、artifact、release 全部依赖模型行为；而 deterministic control plane 能把这些职责固化成可测试 contract。这一点与仓库自己的未来规划、Temporal 的 durable execution 思想、LangGraph 的 persistence/HITL 文档，以及 OpenAI 的 background/eval/safety 方向是同一条线。

## 7.9 四个关键设计决策卡

### 决策 1：控制面由 deterministic state machine 拥有

* **为什么这样做**：可恢复、可取消、可查询、可审计。
* **替代方案**：LangGraph / agent loop 直接驱动全流程。
* **为什么不选替代方案**：生命周期、重试与质量门会变成隐式行为。
* **工程代价**：中等，需要显式 stage 与 event schemas。
* **对当前仓库意味着什么**：保留 `services/research_jobs`，但把它提升为唯一控制面；graph 降为可选子流程。

### 决策 2：`status` 与 `audit_gate_status` 分离

* **为什么这样做**：执行完成不等于质量通过。
* **替代方案**：把 review 继续塞进 job status。
* **为什么不选替代方案**：API contract 脏、监控难、用户理解差。
* **工程代价**：中等，需要改 schema、viewer、tests。
* **对当前仓库意味着什么**：修复 `needs_review` 与 `completed+blocked` 并存的问题。

### 决策 3：evidence store 取代“memory”叙事

* **为什么这样做**：研究系统需要可复现实证，不需要模糊记忆。
* **替代方案**：继续混用 `memory/evidence_store.py` 与 file-based memory。
* **为什么不选替代方案**：边界模糊，容易滑向聊天产品。
* **工程代价**：低到中等，主要是命名和 repository 重组。
* **对当前仓库意味着什么**：`memory/store.py` 归档，`memory/evidence_store.py` 迁入 `evidence_store/`。

### 决策 4：MCP 是扩展通道，不是主干真相

* **为什么这样做**：研究主干需要 snapshot/policy/audit，MCP server 未必提供这些。
* **替代方案**：把一切数据接入都外包给 MCP。
* **为什么不选替代方案**：可控性与审计性不足。
* **工程代价**：中等，需要做 `mcp_bridge`。
* **对当前仓库意味着什么**：`mcp_servers/` 不再占位，变成 connector adapter，而不是产品中心。
