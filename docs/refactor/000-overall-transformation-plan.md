# 深度研究系统重构总计划

## 0. 文档状态
- 当前状态：active
- 负责人：Codex
- 起始分支：`main`
- 起始提交：`c4e6d4d`
- 最近更新：`2026-04-20T15:43:56Z`
- 关联审计文件：`docs/专家审查意见/20260420-gpt-5_4_thinking.txt`

## 1. 背景与目标

### 1.1 项目当前定位
- 当前本质是什么：CLI-first、本地 SQLite + 本地文件系统 + subprocess worker 驱动的可信研究原型；公开主链路由 `main.py + services/research_jobs/` 驱动。
- 当前不是什么：不是已支持的 HTTP/API server，不是企业级多租户平台，不是已完成的 web 产品，也不是可用 benchmark 分数证明发布成熟度的系统。
- 与目标产品愿景的核心差距：runtime substrate、状态一致性、lease/fencing、event/checkpoint 原子性、恢复正确性、fetch/security 边界、claim audit 强度和服务化准备度都未达到产品级。

### 1.2 本次重构目标
- 目标 1：先把 public runtime 的 job lifecycle、lease、event log、checkpoint、recovery 做成可解释且可测试的单机强一致底座。
- 目标 2：收敛 public runtime 与 legacy runtime 边界，避免旧 graph、旧 `auditing` 状态和 benchmark 语义污染未来公开契约。
- 目标 3：逐步补强 connector/policy/snapshot/security、claim/evidence/audit、observability/test/release/API readiness，保证每一步都有验收命令和回滚边界。

### 1.3 非目标
- 本轮不做什么：不直接承诺 HTTP/API server、web UI、多租户、Postgres/对象存储生产迁移、完整企业知识库接入。
- 本轮不承诺什么：不把启发式 claim audit 包装成企业级“已验证”；不把本地 subprocess runtime 说成可横向扩展平台；不把 benchmark/comparator 当作产品发布证明。

## 2. 已阅读清单
- 已阅读文件/目录：
  - `AGENTS.md`：确认当前公开 runtime、legacy 边界、复杂任务必须先写计划和 worktree 化执行。
  - `PLANS.md`：确认当前 release train、active phase 为 `specs/phase-05-report-delivery.md`，以及 phase1-4 已落地但仍有限。
  - `docs/architecture.md`：确认当前架构文档描述的是已落地 runtime/legacy 事实，不是未来产品架构。
  - `specs/phase-05-report-delivery.md`：确认当前 active phase 的目标是 evidence-first report delivery。
  - `docs/adr/adr-0003-runtime-model.md`、`docs/adr/adr-0005-process-job-orchestrator.md`、`docs/adr/adr-0004-connector-contract.md`、`docs/adr/adr-0006-claim-auditing-stage.md`：确认 runtime、connector、audit 的已接受边界。
  - `docs/codex/REFACTORING_PLAYBOOK.md`：确认本次必须分 phase、独立 worktree、先落总计划和 phase 文档。
  - `docs/codex/TEMPLATE-OVERALL-TRANSFORMATION-PLAN.md`、`docs/codex/TEMPLATE-PHASE.md`：确认本文档与每阶段文档结构。
  - `docs/专家审查意见/20260420-gpt-5_4_thinking.txt`：确认 P0/P1/P2/P3 问题分级和代码证据方向。
  - `main.py`：确认公开 CLI 为 `submit/status/watch/cancel/retry`，`legacy-run` 为 hidden 兼容入口。
  - `services/research_jobs/models.py`、`store.py`、`service.py`、`worker.py`、`orchestrator.py`：确认 job row、event、checkpoint、lease、heartbeat、stale recovery、阶段流转的真实实现。
  - `workflows/states.py`：确认 `ResearchState` 与 `JobRuntimeRecord` 存在状态字段重叠。
  - `tests/test_phase2_jobs.py`、`tests/test_phase4_auditor.py`：确认现有测试覆盖 schema/happy path/cancel-retry 基础/audit blocked path，但缺少并发与强恢复测试。
- 每项为什么重要：上述文件共同决定当前事实、公开 surface、迁移边界、审计问题优先级和可验收范围。
- 未读到或不存在的路径：`artifacts/schemas/` 不存在，当前 schema 位于 `schemas/`；未逐行深读全部 `agents/`、`evaluation/`、`scripts/`、`memory/`。
- 对置信度的影响：对 public runtime、state、lease、event/checkpoint、audit 阶段边界的判断置信度高；对 benchmark/comparator 内部指标和全部 legacy agent 细节置信度中等。

## 3. 代码现实地图（Reality Map）

### 3.1 当前真正可运行的主链路
- 入口：`uv run python main.py submit/status/watch/cancel/retry`。
- 主执行链路：`main.py submit` -> `ResearchJobService.submit()` -> `ResearchJobStore.upsert_job()` + 初始 checkpoint -> 本地 subprocess `services.research_jobs.worker` -> `attach_worker()` + heartbeat thread -> `ResearchJobOrchestrator.run()` -> `clarifying -> planned -> collecting -> extracting -> claim_auditing -> rendering` -> report/bundle/trace/audit sidecar。
- 关键状态落点：`workspace/research_jobs/jobs.db` 中的 `jobs`、`job_events`、`job_checkpoints` 表，以及 `workspace/research_jobs/<job_id>/checkpoints/*.json`。
- 关键 artifact：`report.md`、`bundle/report_bundle.json`、`bundle/trace.jsonl`、`audit/claim_graph.json`、`audit/review_queue.json`、`snapshots/`。

### 3.2 当前公开 surface
- 当前支持的入口：CLI `submit/status/watch/cancel/retry` 和本地 report bundle 文件合同。
- 当前不支持的入口：HTTP/API server、web UI、多租户 job API、外部 queue/worker pool。
- 面向产品的真实公开契约：job-oriented CLI + `workspace/research_jobs/<job_id>/` artifacts；CLI 是开发/调试客户端，不是长期产品契约。

### 3.3 public runtime 与 legacy runtime 边界
- public runtime：`main.py` 的非 hidden job 命令、`services/research_jobs/`、`connectors/`、`policies/`、`auditor/`、`artifacts/`。
- legacy runtime：`workflows/graph.py`、`agents/*` 的 legacy graph 节点、hidden `legacy-run`、benchmark/comparator 依赖的旧路径。
- 仍然耦合的部分：public orchestrator 仍调用 `agents.planner/researcher/verifier/writer`，`ResearchState` 来自 `workflows/states.py`，`ACTIVE_JOB_STATUSES` 仍包含旧 `auditing`。
- 当前迁移风险：若直接开放 API，会固化旧状态名、双状态源、legacy graph 字段和本地路径 artifact 形态。

### 3.4 作业生命周期与恢复语义
- status / stage：`created/clarifying/planned/collecting/extracting/claim_auditing/rendering/completed/failed/cancelled/needs_review` 是 public 目标路径；`auditing` 仍残留。
- checkpoint：每阶段后写 checkpoint JSON 和 DB metadata；序号由 `SELECT MAX(sequence)+1` 生成；写入使用 `INSERT OR REPLACE`。
- event log：`job_events` 以 `(job_id, sequence)` 为主键；序号同样由 `MAX(sequence)+1` 生成；`ResearchJobService._append_event()` 当前对同一事件取号两次。
- retry / cancel：cancel 只写 `cancel_requested=True`，orchestrator 在阶段边界检查；retry 基于最新 checkpoint 创建新 job。
- heartbeat / stale recovery：worker 启动时 `attach_worker()` 覆盖 `worker_pid/worker_lease_id`；heartbeat lease mismatch 只拒绝更新心跳，不 fence 阶段推进；stale recovery 通过 heartbeat + PID 推断后重新 spawn worker。
- 已知边界与缺陷：没有原子 lease acquire；没有 lease fencing；event/checkpoint 不是事务化 append-only；runtime row 与 checkpoint state 不是单一可信状态源。

### 3.5 connector / policy / snapshot / audit / benchmark 关系图
- connector：`connectors/registry.py` 统一 search/fetch/file-ingest，但 web/github/arxiv 主要仍是旧工具 adapter。
- source policy：`policies/source_policy.py` 对候选 URI 做 allow/deny 过滤，不是 outbound fetch 安全边界。
- snapshot：`connectors/snapshot_store.py` 持久化文本 snapshot manifest/raw text，未形成对象存储/去重/index 平台层。
- audit：`auditor/pipeline.py` 产出 claim graph/review queue/blocked gate；当前判定主要是启发式 token overlap 和 marker。
- benchmark / comparator：仍是 diagnostics/research 工具，不是 public runtime 发布证明。
- 当前耦合问题：public runtime 依赖 legacy agents 产出 summary/source；benchmark 指标和 runtime 成熟度容易被混读；audit artifact 与 report bundle 需要继续保持一致。

### 3.6 web/API 产品化复用面与技术债
- 可复用：Pydantic 模型、schema、report bundle、部分 connector contract、source policy 数据模型、audit sidecar 结构、CLI job lifecycle 语义。
- 必须重做：多实例 worker ownership、server API/auth/tenant、生产持久层、artifact/object storage、centralized fetch security、observability。
- 高风险技术债：本地 subprocess worker、SQLite 单文件运行时、双状态源、非原子序号、启发式 audit、legacy/new runtime 混杂。

## 4. 审计问题分级映射

### 4.1 P0
| 问题 | 影响模块 | 风险 | 计划 phase | 验证方式 |
|---|---|---|---|---|
| worker lease / stale recovery 非并发安全 | `services/research_jobs/store.py`, `service.py`, `worker.py`, `orchestrator.py` | 双 worker/split-brain，artifact 与 audit 双写失真 | Phase 1 | lease acquire/fencing 单元测试、stale recovery 竞争测试、CLI smoke |
| event/checkpoint 序号非事务化且可 replace | `services/research_jobs/store.py`, `service.py`, `orchestrator.py` | trace 覆盖/乱序，审计不可回放 | Phase 1 | append-only 冲突测试、单事件单取号测试、checkpoint monotonic 测试 |
| 双状态源：`JobRuntimeRecord` vs `ResearchState` | `models.py`, `orchestrator.py`, `workflows/states.py` | status/API/UI/recovery 读到不同真相 | Phase 2 | canonical projection 测试、resume/status 一致性测试 |
| 本地 CLI/subprocess/SQLite/path runtime 不是平台底座 | `main.py`, `services/research_jobs/*`, `workspace/` artifact contract | web/API 化时调度、存储、租户、并发全部返工 | Phase 6 | API readiness contract 文档与服务边界测试 |

### 4.2 P1
| 问题 | 影响模块 | 风险 | 计划 phase | 验证方式 |
|---|---|---|---|---|
| allow/deny domain 不是 fetch 安全边界 | `connectors/registry.py`, `policies/source_policy.py`, `tools/web_scraper.py` | SSRF、redirect 绕过、私网抓取 | Phase 3 | URL canonicalization、私网/redirect/size/content-type 拦截测试 |
| claim audit 是启发式 overlap | `auditor/pipeline.py`, `auditor/models.py`, `artifacts/bundle.py` | “已审计”语义误导 | Phase 4 | evidence span/citation grounding 测试、blocked/review queue 回归 |
| legacy/new runtime 混杂与阶段名漂移 | `main.py`, `workflows/*`, `services/research_jobs/*` | 错误状态名进入公开契约 | Phase 2 | public status vocabulary 测试、legacy-run 兼容测试 |
| 失败路径测试不足 | `tests/` | 回归保护不能覆盖最危险 failure mode | Phase 1-5 | 每 phase 新增 targeted failure tests |

### 4.3 P2
| 问题 | 影响模块 | 风险 | 计划 phase | 验证方式 |
|---|---|---|---|---|
| connector substrate 仍偏旧工具包装 | `connectors/*`, `policies/*` | 新来源、权限、索引和去重会返工 | Phase 3 | connector contract tests、snapshot provenance tests |
| benchmark / LLM judge 不能作为发布证明 | `evaluation/*`, `scripts/*` | 发布口径偏离 runtime 可靠性 | Phase 5 | release checklist 与 reliability test suite |
| `_merge_state()` 浅合并 | `orchestrator.py`, `workflows/states.py` | 嵌套状态/人审/API patch 易错 | Phase 2 | explicit reducer/command tests |

### 4.4 P3
| 问题 | 影响模块 | 风险 | 计划 phase | 验证方式 |
|---|---|---|---|---|
| SQLite 使用仍偏脚本级 | `store.py` | 锁竞争、性能和服务迁移成本 | Phase 5/6 | WAL/busy timeout/index tests 或迁移设计 |
| 文档广度高于底层成熟度 | `README*`, `docs/*`, `specs/*` | 对外预期误导 | Phase 5 | 文档事实审计与公开 surface 检查 |

## 5. 分阶段改造路线

## Phase 0：基线盘点、契约冻结、计划落盘
- 目标：恢复 Git 历史，确认模板/审计文件在 `HEAD` 可见，落地总计划，冻结当前公开 runtime/legacy 边界。
- 范围：`AGENTS.md`、`docs/codex/*`、`docs/专家审查意见/*`、`docs/refactor/000-overall-transformation-plan.md`。
- 非目标：不改 runtime 代码，不创建 HTTP/API，不修改 legacy graph 行为。
- 影响目录：`docs/`、根级 Git 元数据。
- 风险：当前 main 工作区存在大量未纳入本次提交的本地差异，后续 worktree 必须从 `HEAD` 创建而不是依赖脏工作区。
- 回滚边界：可 revert Phase 0 文档提交，不影响 runtime。
- 验收标准：5 个输入文件 `git ls-files` 可见且 `git ls-tree HEAD` 可见；总计划文件存在并覆盖 phases、依赖、验收、worktree/branch 命名。
- 必跑命令：`git ls-files --stage -- ...`、`git ls-tree -r --name-only HEAD -- ...`、`git status --short`。
- 合并条件：总计划提交到 `main`；不提交与本 phase 无关的脏工作区文件。

## Phase 1：runtime / state / persistence / lease / event log 基础重构
- 目标：把单机 public runtime 的 lease、event、checkpoint 做成可解释的强一致基础，优先消除双 worker 和审计轨迹覆盖风险。
- 范围：原子 lease acquire/release、lease fencing、heartbeat 语义、append-only event、checkpoint 序号事务化、SQLite 连接基础治理。
- 非目标：不迁移 Postgres，不引入外部 queue，不改 connector/audit 判定逻辑，不开放 API。
- 影响目录：`services/research_jobs/`、`tests/test_phase2_jobs.py` 或新增 runtime tests、`docs/architecture.md`、`docs/refactor/phase-01-runtime-state-persistence.md`。
- 风险：修改 store 基础写入语义可能影响所有 CLI job、watch、retry、bundle trace。
- 回滚边界：revert Phase 1 分支即可恢复旧 SQLite store 行为；已生成的新测试和 phase 文档一并回滚。
- 验收标准：旧 happy path 仍通过；新增测试证明同一 active job 只能被一个 lease 推进；event append 不覆盖；checkpoint sequence 单调；stale recovery 不会覆盖活跃 lease。
- 必跑命令：`uv run pytest -q tests/test_phase2_jobs.py`、`uv run python main.py --help`、`uv run ruff check services/research_jobs tests/test_phase2_jobs.py`。
- 合并条件：Phase 1 文档记录实际修改/验证；定向测试和 CLI help 通过；未扩大到 connector/audit/API。

## Phase 2：job orchestration、恢复语义、取消/重试/幂等、artifact 契约收敛
- 目标：明确 canonical state/projection，收敛 public stage vocabulary，补强 resume/cancel/retry 幂等和 artifact 契约。
- 范围：`JobRuntimeRecord` 与 checkpoint `ResearchState` 的同步边界、public status vocabulary、cancel stage boundary、retry provenance、artifact emitted 时机。
- 非目标：不改变 claim audit 算法，不服务化，不迁移存储。
- 影响目录：`services/research_jobs/`、`artifacts/`、`schemas/`、`tests/`、`docs/architecture.md`。
- 风险：状态字段变化会影响 CLI status/watch、report bundle、legacy benchmark 旁路读取。
- 回滚边界：按 branch revert；保持旧 schema 兼容或提供明确兼容说明。
- 验收标准：resume/status/checkpoint projection 一致；`auditing` 不再作为 public runtime 新 job 路径；cancel/retry 重复调用可预测；bundle job summary 与 runtime row 一致。
- 必跑命令：`uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py`、`uv run python main.py --help`、`uv run python scripts/run_benchmark.py --help`。
- 合并条件：文档说明公开状态词汇和 legacy 兼容策略；无破坏 benchmark/legacy-run 的未解释变更。

## Phase 3：connector / source policy / snapshot / fetch security 重构
- 目标：把 policy 从候选过滤提升为 fetch 前后的真实安全治理边界，并收敛 snapshot provenance。
- 范围：URL canonicalization、domain/IP/redirect 复检、timeout/size/content-type 限制、fetch decision audit、snapshot manifest 一致性。
- 非目标：不接全量企业私有 connector，不做搜索索引平台，不实现多租户权限系统。
- 影响目录：`connectors/`、`policies/`、`tools/web_scraper.py`、`schemas/`、`tests/test_phase3_connectors.py`、文档。
- 风险：更严格 policy 可能让现有 benchmark/source 获取减少；需明确测试 profile 与 production-like profile 差异。
- 回滚边界：可回滚 fetch policy adapter，不影响 Phase 1/2 runtime store。
- 验收标准：私网/IP/redirect/oversized/unsupported content 被拦截并有事件或健康记录；允许来源仍能 snapshot；report bundle 只引用有 snapshot_ref 的 public runtime source。
- 必跑命令：`uv run pytest -q tests/test_phase3_connectors.py`、`uv run pytest -q tests/test_phase2_jobs.py`、`uv run ruff check connectors policies tests`。
- 合并条件：安全边界和退化策略写入架构/phase 文档；benchmark 影响被记录。

## Phase 4：claim / evidence / audit pipeline 重构
- 目标：把 claim/evidence/audit 从启发式 gate 逐步升级为可解释的 grounding/review 流。
- 范围：evidence span/citation locator、claim-support edge 质量字段、unsupported/contradicted/unverifiable 语义、review queue 与 bundle 一致性。
- 非目标：不声称完全自动事实验证，不引入 LLM judge 作为唯一 gate，不做复杂人工审核平台。
- 影响目录：`auditor/`、`artifacts/`、`schemas/`、`workflows/states.py`、`tests/test_phase4_auditor.py`。
- 风险：改变 audit summary 字段会影响 report bundle 和 Phase 05 report delivery。
- 回滚边界：保持 schema version 或兼容字段；可回滚 audit pipeline，不影响 Phase 1/2 runtime guarantees。
- 验收标准：关键 claim 必须有 evidence edge 或进入 review queue；bundle、claim graph、review queue 交叉引用一致；blocked/passed 语义不误导。
- 必跑命令：`uv run pytest -q tests/test_phase4_auditor.py tests/test_phase2_jobs.py`、`uv run ruff check auditor artifacts tests`。
- 合并条件：文档明确“已实现的 audit 强度”和“仍需人工/后续增强”的边界。

## Phase 5：observability、测试体系、发布工程、配置治理
- 目标：把 runtime reliability、安全回归、audit correctness 纳入 release gate，降低 benchmark 叙事误导。
- 范围：targeted failure test suite、trace/recovery metrics、config domain 分层、README/docs 事实审计、release checklist。
- 非目标：不做外部监控 SaaS 集成，不做完整 SLO 平台。
- 影响目录：`tests/`、`evaluation/`、`scripts/`、`configs/`、`docs/`。
- 风险：测试收紧可能暴露既有 flake 或慢测试，需要区分必跑和扩展回归。
- 回滚边界：测试与文档可独立回滚，不改变 Phase 1-4 核心契约。
- 验收标准：release gate 不再只依赖 benchmark/report-shape；配置项按 runtime/legacy/benchmark/connector/audit 分层；README 不夸大当前能力。
- 必跑命令：`uv run pytest -q`、`uv run ruff check .`、`uv run python scripts/run_benchmark.py --help`、`uv run python scripts/full_comparison.py --help`。
- 合并条件：全量或明确范围回归通过；若有跳过，必须记录原因和风险。

## Phase 6：web/API readiness 与 server surface 铺底
- 目标：只做 server/API readiness 的底层契约准备，不把未来能力写成当前能力。
- 范围：API contract 草案、job service boundary、artifact service boundary、auth/tenant/storage/queue ADR、迁移兼容策略。
- 非目标：不在本 phase 交付正式 HTTP server 或 UI；不承诺多租户生产可用。
- 影响目录：`docs/adr/`、`specs/`、`services/` 边界文档、必要 schema。
- 风险：过早编码 server 会固化未成熟 runtime；本 phase 必须优先契约和边界。
- 回滚边界：ADR/spec 回滚不影响 CLI runtime。
- 验收标准：API readiness 只描述目标边界和可复用 contracts；明确当前没有 supported HTTP/API surface；server 实现进入下一 release train。
- 必跑命令：`uv run python main.py --help`、`uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py`。
- 合并条件：ADR/spec 被更新；没有新增半成品 server public surface。

## 6. worktree / branch / merge 策略

### 6.1 命名规范
- worktree：`../dra-phase-XX-<short-name>`
- branch：`refactor/phase-XX-<short-name>`
- phase 文档：`docs/refactor/phase-XX-<short-name>.md`
- Phase 1 具体命名：
  - worktree：`../dra-phase-01-runtime-state-persistence`
  - branch：`refactor/phase-01-runtime-state-persistence`

### 6.2 每阶段执行流程
1. 从 `main` 的最新验收提交创建独立 worktree。
2. 在 worktree 中先生成 phase 文档，写明范围、非目标、风险、回滚、验收、命令、合并条件。
3. 按 TDD 增加失败测试，再实现最小必要 runtime/doc/schema 修改。
4. 执行 phase 必跑命令并把实际结果写回 phase 文档。
5. 验收通过后提交 phase 分支，回到 main 合并，更新本总计划状态看板，再进入下一 phase。

### 6.3 合并策略
- merge back to main 的条件：phase 文档 accepted；定向测试通过；文档同步；没有无关文件混入；`git diff --name-only main...phase` 与 phase 范围一致。
- 何时 squash：phase 中有多次红绿试验提交但最终只需要一个审计清晰提交时 squash。
- 何时保留历史：phase 内多个可独立回滚的子任务各自通过验收时保留 merge commit 或线性多提交。

### 6.4 回滚策略
- 阶段失败时如何回滚：关闭 worktree 或 revert phase 分支；main 不合并未验收 phase。
- 哪些数据/文档必须保留：失败原因、命令输出摘要、未解决风险写入 phase 文档；如果未合并，必要信息回写总计划的风险/开放问题。

## 7. 不变量与通用验收门槛
- 不变量 1：同一 active job 不能被两个有效 worker lease 同时推进。
- 不变量 2：event sequence 对单个 job 单调递增、append-only、不可静默覆盖。
- 不变量 3：checkpoint sequence 对单个 job 单调递增，active checkpoint 与 runtime status 可解释。
- 文档一致性门槛：`docs/architecture.md` 只描述当前已落地事实；spec/ADR 描述目标边界；不得把未来 API/server/web 能力写成当前能力。
- 测试门槛：有 runtime/state/lease/event/recovery/audit/security 行为变更必须有 targeted tests；公共契约变更必须更新 schema/docs。
- 公开契约门槛：CLI `submit/status/watch/cancel/retry` 保持可用；`legacy-run`、benchmark/comparator 只在明确 phase 范围内调整。

## 8. 当前阶段状态看板
| Phase | 状态 | worktree | branch | 最近结果 | 下一步 |
|---|---|---|---|---|---|
| Phase 0 | completed | main | main | Git 历史已恢复；重构输入文件与总计划已提交 | 已进入 Phase 1 |
| Phase 1 | merged | `../dra-phase-01-runtime-state-persistence` | `refactor/phase-01-runtime-state-persistence` | 已合并 `8884453`；`tests/test_phase2_jobs.py` 15 passed，`tests/test_phase4_auditor.py` 7 passed，`pytest -q` 155 passed，ruff 全量通过 | 已进入 Phase 2 |
| Phase 2 | merged | `../dra-phase-02-orchestration-recovery-contract` | `refactor/phase-02-orchestration-recovery-contract` | 已合并 `18fffb3`；`tests/test_phase2_jobs.py` 21 passed，`tests/test_phase4_auditor.py` 7 passed，`pytest -q` 161 passed，ruff 全量通过 | 已进入 Phase 3 |
| Phase 3 | merged | `../dra-phase-03-connector-policy-security` | `refactor/phase-03-connector-policy-security` | 已合并 `9ca45ba`；`tests/test_phase3_connectors.py` 16 passed，`tests/test_phase2_jobs.py tests/test_phase4_auditor.py` 28 passed，`pytest -q` 164 passed，ruff 全量通过 | 已进入 Phase 4 |
| Phase 4 | merged | `../dra-phase-04-claim-evidence-audit` | `refactor/phase-04-claim-evidence-audit` | 已合并 `e0fef2b`；`tests/test_phase4_auditor.py` 8 passed，`tests/test_phase2_jobs.py tests/test_phase3_connectors.py` 37 passed，`pytest -q` 165 passed，ruff 全量通过 | 已进入 Phase 5 |
| Phase 5 | merged | `../dra-phase-05-observability-release-governance` | `refactor/phase-05-observability-release-governance` | 已合并 `f4b6987`；targeted 回归 15 passed，`pytest -q` 167 passed，ruff 全量通过，benchmark/comparison help 通过 | 更新总计划后进入 Phase 6 |
| Phase 6 | planned | `../dra-phase-06-api-readiness` | `refactor/phase-06-api-readiness` | 未开始 | 创建 Phase 6 worktree，补齐 API readiness 契约 |

## 9. 风险与开放问题
- 风险 1：当前 main 工作区除已提交的 5 个输入文件外仍有大量本地修改；后续 phase worktree 必须基于 clean `HEAD`，不要误用主工作区脏文件。
- 风险 2：Phase 1 修改 store 写入语义会影响所有 job runtime 路径；必须先红绿测试再实现。
- 开放问题 1：长期持久层是否迁 Postgres/object storage/queue，本轮只做 readiness，不在 Phase 1-5 强行落地。
- 开放问题 2：claim audit 的下一代 grounding 是否使用 LLM 辅助、retrieval scorer 或人工 review UI，Phase 4 先锁定结构化可解释边界。

## 10. 下一步
- 立即下一步：提交 Phase 5 后的总计划更新，创建 `../dra-phase-06-api-readiness` worktree 和 `refactor/phase-06-api-readiness` 分支。
- 进入下一阶段的条件：Phase 5 merge commit 在 `main`；总计划状态看板已更新；Phase 6 worktree 从最新 `main` 创建成功。
