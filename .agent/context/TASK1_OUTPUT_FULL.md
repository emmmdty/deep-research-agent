以下内容按你要求的顺序组织：**仓库审计 → 联网调研 → 差距分析 → 升级总方案**。
前置假设只有两条：第一，审计边界是该仓库当前公开 `main` 分支的关键文件与目录；第二，本方案按“**单团队内部研究服务 + 面试/作品集项目**”来设计，因此会把多租户 IAM、复杂合规与大规模 SaaS 运维放到后续边界，而不是首期强行做满。这是推断。

---

# 1. 执行摘要

这个仓库的真实水平，**高于普通求职 demo**。它已经不是“只有一个 LangGraph agent loop 的玩具壳子”，而是已经长出了几块很有价值的雏形：CLI-first 的异步 job 运行时、SQLite 持久化的 job / event / checkpoint、source policy 与 domain allow/deny、snapshot store、claim-level audit、phase 化 specs、以及围绕 phase2/3/4 的测试与 release gate。仓库文档甚至已经明确提出：未来不应继续把“多智能体图”当成产品主架构，而应转向 **object contract + deterministic runtime + evidence + audit + release gate**。这说明作者方向感是对的。

它现在还不够企业级，核心原因不是“模型不够强”，而是**产品边界与工程边界还没有完全收拢**：公开入口仍是 CLI，没有受支持的 HTTP/API surface；worker 仍是本地 subprocess + SQLite 模式；connectors 虽然已有 substrate，但大部分还是 `LegacyConnectorAdapter` 包旧工具；provider abstraction 仍偏 OpenAI-compatible，缺少 Anthropic 原生支持；memory/evidence 边界不统一；report bundle 与 review workflow 还没有成为一等公民；旧 benchmark/comparator 叙事仍然压着新 runtime/audit 主线。仓库自己的 `specs/api-readiness-contract.md`、`PLANS.md` 和 `specs/evaluation-protocol.md` 其实已经把这些问题点得很清楚。

这次升级的核心转向应当非常明确：**从“LangGraph 多智能体研究 demo”升级为“企业级、证据优先、可恢复、可审计、可评测、可服务化的 Deep Research Job System”**。控制面由 deterministic state machine 接管；LLM 只负责规划、抽取、审计辅助与综合，不再拥有生命周期；source governance、snapshot、claim graph、audit gate、report bundle、release gates 成为主架构的一部分，而不是附属脚本。这个方向与 OpenAI 2025–2026 的 Deep Research / Background Mode / Connectors / Eval 实践，以及 MCP、durable execution、trace grading 等官方资料高度一致。

最终项目在简历/面试中的定位，不应是“我做了一个会搜网页写报告的 agent”，而应是：**“我把一个 agent demo 重构成了企业级 Deep Research Runtime：支持异步任务、来源治理、快照留痕、claim 级证据审计、报告包导出、恢复/取消/重试、以及 release-gated evals，面向公司/行业深度研究场景。”** 这才是 Staff 级 AI 应用研发 / AI Agent 工程岗位会认真看的项目定位。

---

# 2. 当前仓库审计报告

## 2.1 当前公开面与 runtime 事实

当前仓库的**公开入口**是 `main.py` 及其对应的 CLI。README 把仓库定位为 **public research-engineering / portfolio project**，强调多源证据、结构化 citation、benchmark/comparator harness 与工程文档；当前受支持的 public surface 是 CLI-first，而不是 HTTP API。`specs/api-readiness-contract.md` 也明确写了：当前公开入口是 `submit/status/watch/cancel/retry`，并且**没有受支持的 HTTP/API server、web UI、多租户 job API、外部 queue/worker pool**。

当前**runtime 主体**已经不是纯 LangGraph loop，而是 `services/research_jobs/` 下的 deterministic job orchestrator：有 job model、store、service、worker、checkpoint、heartbeat、stale-job recovery，状态枚举包含 `created / clarifying / planned / collecting / extracting / auditing / claim_auditing / rendering`，终态包含 `completed / failed / cancelled / needs_review`。`specs/phase-02-job-orchestrator.md` 明确把“minutes-level 研究任务需要 background execution、status query、cancel/retry/recovery”设为必要目标。

当前**legacy 部分**仍然很多：`agents/`、`workflows/`、旧的 multi-agent graph、以及 connector 层里的 `LegacyConnectorAdapter` 都还在。`docs/development.md` 已经把 `legacy-run` 定义成 migration validation，而不是长期 contract；`PLANS.md` 更是直接写明：**不要把当前 multi-agent graph 继续当成未来产品主架构**，benchmark/comparator 输出只应作为 migration diagnostics，而不是产品真相。

当前**benchmark / comparator / ablation 资产**是存在的：`evaluation/benchmarks/`、`evaluation/comparators.py`、`evaluation/llm_judge.py`、`evaluation/metrics.py`、`scripts/run_ablation.py`、`scripts/run_benchmark.py`、`scripts/full_comparison.py`、`scripts/run_portfolio12_release.py` 都在；release gate 也已经要求 benchmark diagnostics 和 docs surface honesty。但 repo 自己的 `specs/evaluation-protocol.md` 与 `PLANS.md` 已明确否定“按报告长度、节数、关键词命中、citation 数量”来判断好坏。

当前**claim audit / connector substrate / source policy / snapshot / memory** 并非空白。`auditor/` 已经有 `ClaimRecord`、`ClaimSupportEdgeRecord`、`ConflictSetRecord`、`ClaimReviewQueue`、`AuditDecision`，并可输出 `claim_graph.json` 与 `review_queue.json`；`connectors/` 已有统一 candidate/fetch 模型、snapshot store、URI 安全检查、`files/github/arxiv/open_web` 注册；`policies/` 已有 source profile、allow/deny domain、auth_scope、budget guardrails；`memory/` 则同时存在 `evidence_store.py` 的 SQLite evidence store 和一个偏 file-based 的 `store.py`。问题不在于“没有”，而在于这些能力还没有完全收拢成企业级产品边界。

## 2.2 当前状态事实表

* **已存在：CLI-first 的异步 job 入口与基本作业控制。** 仓库 README 与 API readiness 文档都把 CLI 作为当前对外入口，支持 submit/status/watch/cancel/retry。
* **已存在：deterministic job runtime 雏形。** `services/research_jobs` 已有 stateful store、checkpoint、worker lease、heartbeat、stale recovery，不再只是单次 agent loop。
* **已存在：source policy / budget / snapshot 基础设施。** source profiles、allow/deny domain、auth_scope、budget guardrails、snapshot_ref 已进入 phase03 与测试。
* **已存在：claim-level audit 雏形。** phase04 已要求 claim graph、support edges、conflict set、critical claim review queue、blocked gate semantics。
* **部分存在：report bundle 与可交付 artifacts。** README 已有 `report.md / report_bundle.json / trace.jsonl / snapshots / audit` 的产物设定，但 phase05 仍在“从长报告转向 bundle”阶段。
* **部分存在：connector substrate，但核心实现仍偏 legacy adapter。** `open_web/github/arxiv` 多数经 `LegacyConnectorAdapter` 走旧工具链。
* **部分存在：benchmark / comparator / release gate。** 有脚本、有测试、有 gate 配置，但旧评价范式仍未完全退出主叙事。
* **缺失：受支持的 HTTP API、batch service、server-grade queue / object storage。** `specs/api-readiness-contract.md` 明确说明这些尚未对外支持。
* **缺失：Anthropic 原生 provider 与真正的多 provider 路由。** 当前 `llm/provider.py` 主要是 OpenAI-compatible 封装；`configs/settings.py` 默认 provider 也是 MiniMax/DeepSeek/Agicto/OpenAI，未体现 Anthropic 原生通道。
* **不合理：执行状态与质量状态混在一起。** 一边有 `needs_review` 作为终态，另一边 phase04 又强调 `completed + audit_gate_status=blocked` 语义，当前 contract 不够干净。
* **应归档：multi-agent graph 作为产品真相、report-shape 指标、toy-ish memory store、占位型 MCP 目录。** 这些要么被 `PLANS.md` 明确降级，要么不适合作为未来主架构。

## 2.3 当前资产盘点

最值得肯定的是：这个仓库的**规格化意识**已经形成。`docs/` 有 architecture / development / interview_qa / ADR；`specs/` 从 phase01 到 phase06 都已经写出来了；`tests/` 里不仅有 benchmark/comparator 测试，还有 `test_phase2_jobs.py`、`test_phase3_connectors.py`、`test_phase4_auditor.py`。这意味着你不是从零造轮子，而是在一个已经开始“自我纠偏”的工程底座上重构。

第二类资产是**工程内核**：`services/research_jobs/`、`connectors/models.py`、`snapshot_store.py`、`policies/source_policy.py`、`budget_guardrails.py`、`auditor/models.py`、`auditor/pipeline.py`、`artifacts/`。这些模块已经包含企业级系统最重要的几个关键词：state、policy、snapshot、evidence、claim、audit、bundle。它们现在还粗，但方向对。

第三类资产是**迁移诊断资产**：`evaluation/benchmarks/`、`evaluation/comparators.py`、`scripts/run_ablation.py`、`scripts/run_portfolio12_release.py`、历史输出、测试文化、ruff / pytest 配置。这些不该再主导产品架构，但非常适合在重构过程中做 regression baseline、ablation 与 interview 叙事。

## 2.4 当前技术债

第一笔技术债是**主叙事错位**。README 开头仍在用 “LangGraph-based deep research agent / multi-agent workflow” 讲项目，而 repo 自己的 `PLANS.md` 已经要求把 multi-agent graph 降级为 legacy runtime。也就是说，仓库现在“实际最有价值的东西”与“对外讲述的东西”不是同一套。对于面试项目，这会直接减分。

第二笔技术债是**provider 与数据面不完整**。`llm/provider.py` 还是 OpenAI-compatible 统一壳，Anthropic 原生能力、base_url 双栈、provider capability routing 都没有成型；`mcp_servers/` 几乎还是占位；prompt 层也很薄。仓库 metadata 仍标注为 Alpha，并且依赖里混着 `gpt-researcher`、`langgraph`、`langchain-*` 等实验性痕迹，说明核心与实验边界还未完全分离。

第三笔技术债是**状态与存储边界混乱**。`memory/evidence_store.py` 和 `memory/store.py` 代表了两套不同的“memory”想法；而企业级研究系统真正需要的不是模糊 memory，而是明确的 `job store / document store / snapshot store / evidence store / artifact store`。当前这种混合命名会让系统继续往“聊天机器人记忆”方向漂。

## 2.5 当前 repo 中值得保留 / 迁移 / 归档 / 删除的内容

**保留（Keep）**
保留 `services/research_jobs` 的作业生命周期思想与大部分事件/检查点逻辑；保留 `connectors/models.py`、`snapshot_store.py`、URI safety、`policies/` 与 `source-profiles/`；保留 `auditor/models.py` 与 `pipeline.py` 的 claim/support/conflict 思想；保留 `artifacts/`、`specs/`、phase2/3/4 测试、release gate 文化；保留 `tools/web_search.py`、`github_search.py`、`arxiv_search.py` 作为迁移种子；保留 `main.py` 但降级为 developer/debug CLI wrapper。

**迁移（Migrate）**
把 `services/research_jobs/` 迁入新的核心 runtime 包；把 `connectors/legacy.py` 与旧 tool 调用迁成真正的一等 connector；把 `memory/evidence_store.py` 迁入统一 evidence/document store；把 `llm/provider.py` 迁为 `providers/` 目录下的多 provider 适配器；把 `evaluation/*` 与 `scripts/*` 迁成新的 `evals/` 体系；把 `research_policy.py`、`agents/researcher.py`、`agents/verifier.py` 的有效逻辑拆散回 stage executor、extractor、auditor。

**归档（Archive）**
把 `agents/`、`workflows/`、`legacy-run` 路径、旧 comparator narrative、`evaluation/metrics.py` 中的 report-shape 打分、`memory/store.py`、占位型 `mcp_servers/` 全部归入 `legacy/` 或 `evals/legacy_diagnostics/`。它们仍可保留为 migration diagnostics，但不再进入未来公开产品主线。

**删除（Delete）**
删除“把 word count / section count / keyword hit / raw citation count 当作好坏指标”的 release 判定逻辑；删除任何把多 agent 数量当核心卖点的文档与展示；删除未来核心路径中对旧 comparator 的硬依赖。这个删除不是风格调整，而是产品边界纠偏。

---

# 3. 联网调研结论

证据分级说明：
**强证据**：官方 API docs、官方 SDK docs、官方规范、官方仓库主干文档。
**中等证据**：官方 cookbook、官方产品页、官方模型卡。
**弱证据**：官方 OSS 示例或第三方开源实现。

## 3.1 A. 深度研究 Agent 的现代产品形态

2025–2026 的主流 Deep Research 形态，已经不再是“单轮问答 + 长回复”，而是**后台异步任务、可轮询状态、来源受控、可中断、带 citations 的最终交付物**。OpenAI 官方把 Background Mode 定义为运行长任务的异步能力，支持后台执行与轮询状态；Web Search 文档则把 deep research 区分为多分钟、可使用大量来源的研究型工作流，并支持 `allowed_domains` 与 `url_citation`。

OpenAI 的 ChatGPT Deep Research 产品页进一步把现代研究产品的公开形态说得很清楚：**可导入 approved URLs、private files、apps；可 review 计划、实时跟踪进度、随时 interrupt / redirect；完成后可通知、可分享、可下载 PDF/DOCX；并且对企业环境提供 source controls 与权限管理。** 这组能力与用户要求的 `asynchronous / progress tracking / interrupt / retry / resume / report bundle / trusted source restriction` 基本同构。对本项目的启示是：**你要做的是“研究作业系统”，不是“聊天壳子”。** 强证据是官方 API 文档；中等证据是官方产品页。

## 3.2 B. Agent runtime / orchestration

官方与主流框架都在强调：**长任务的可靠性来自 durable execution，不来自提示词魔法。** Temporal 的官方文档把 durable execution 描述为可跟踪进度、跨失败恢复、保存 event history，并原生支持 query / signal / cancel / update；LangGraph 官方则明确把 persistence / checkpointer / interrupt / HITL 作为 durable execution 能力，并要求开发者为 side effects 保持 idempotent。

对本项目最重要的结论不是“必须上 Temporal”或“必须用 LangGraph”，而是：**生命周期 ownership 必须落在 deterministic state machine，而不是 agent loop。** 这恰好和仓库自己的 `PLANS.md` 一致。OpenAI Background Mode 也说明了另一点：provider-native async 很有用，但它只是模型调用层的后台执行；它不会替你处理 source policy、snapshot、claim audit、artifact manifest，而且 OpenAI 官方还明确写了 background mode 为轮询会保留响应数据、**不兼容 ZDR**。所以企业级研究系统不能把控制面外包给单一 provider。

## 3.3 C. 数据接入与 connector

OpenAI 官方已经把 Connectors / MCP 放进 Responses API 与 Deep Research 相关能力里；MCP 官方规范也已经稳定到 resources / tools / prompts 三类能力，以及 stdio 与 HTTP transport、可选的授权规范。这说明“AI 应用通过统一 connector / app integration 接入外部系统”已经是主流工程方向。

但对这个项目来说，关键不是“兼容 MCP 就够了”，而是：**任何 connector 输出都必须穿过 source policy、budget、snapshot、freshness、auditability 这一层。** MCP 适合作为扩展通道，不适合作为可信研究主干本身。OpenAI 的 Web Search 与 File Search 能提供 provider-native 搜索/检索能力，但它们不能替代你自己的 snapshot 与 provenance contract；相反，它们更像是可插拔的 search backend 或 retrieval assist。强证据来自 MCP 规范与 OpenAI 文档；弱证据来自 LangChain 的开源 deep research agent 示例，它已经把多 provider、search 和 MCP server 作为 baseline。

## 3.4 D. 研究方法论核心

OpenAI 的 Deep Research 指南强调源选择应按任务域优先官方/原始来源；Reasoning Best Practices 则给出很清晰的角色分工：**reasoning model 更适合做 planner / decomposition / hard judging，普通高吞吐模型更适合做执行 workhorse**。OpenAI 的 agent safety 指南又进一步要求：**不要让 untrusted data 直接驱动 agent 行为；外部输入应该被抽成结构化字段并经过验证。** Anthropic 的一致性文档也把 structured outputs 列为首选手段之一。

这些官方材料对本项目的直接意义是：方法论不能再停留在“Planner 让 Researcher 去搜，再让 Writer 去写”。企业级 Deep Research 必须把问题分解、source taxonomy、multi-query diversification、evidence fragment、claim-support-edge、conflict/uncertainty、structured audit 全部变成**可验证对象**。这是你后面白皮书设计的基础。

## 3.5 E. 模型与 provider abstraction

用户要求 OpenAI、Anthropic、以及自定义 `base_url` 双栈兼容，这一点在官方 SDK 层面是可行的。OpenAI 官方 SDK 支持 sync / async client，并允许通过 `base_url` 或 `OPENAI_BASE_URL` 指向兼容后端；Anthropic 官方 Python SDK支持 sync / async、streaming，并且 SDK 代码与 CLI 都支持 `ANTHROPIC_BASE_URL` / `base_url` 这类基础地址覆盖；Anthropic 官方还提供了 OpenAI SDK compatibility 文档。

这意味着本项目完全可以做到：**原生 OpenAI + 原生 Anthropic + OpenAI-compatible + Anthropic-compatible** 四类 provider profile 共存。关键不是 SDK 能不能接，而是不要把系统控制面写死在某一家 API 的 tool semantics 上。provider-native web / file / reasoning / judge 可以接入，但 source policy、snapshot、claim audit、release gate 必须是你自己的系统能力。

## 3.6 F. 评测与实验

OpenAI 官方对 eval 的态度很明确：**eval-driven development、task-specific evals、log everything、automate when possible、用 human feedback 校准自动打分**。`Working with evals` 把它比作类似 BDD 的过程；`Evaluate agent workflows` 又强调应先从 representative trace 的 grading 开始，再发展出稳定数据集和 grader。

仓库自己的 `specs/evaluation-protocol.md` 与 phase06 其实和这一套非常一致：把 `Claim`、`Task rubric item`、`Job run` 作为核心评测对象，关注 critical claim support precision、citation error、provenance completeness、conflict detection、uncertainty honesty、resume success、policy compliance、adversarial robustness，而明确反对按原始篇幅与 citation 数量打分。结论很直接：**这套仓库内生评测思想应该升级为正式 eval 平台，而不是废弃。**

## 3.7 G. 企业级落地要素

API 与服务层面，FastAPI 仍然是 Python 里最合适的选择之一：原生 async/await、类型提示、自动 OpenAPI 文档、适合做 typed HTTP surface。持久化层面，SQLAlchemy 官方 async 文档足够成熟，但它也明确提醒 `AsyncSession` **不能在多个并发任务间共享**，这会直接影响 worker / session scope 设计。队列层面，Redis Streams 的 consumer groups 天然支持“一个 group 多 consumer、每条消息分配给其中一个 consumer、并需要 ack”的语义，非常适合中等规模 job dispatch。

可观测性层面，OpenTelemetry 仍是最稳妥的 vendor-neutral 选项；schema 层面，Pydantic v2 + JSON Schema 适合同时服务 API contract、artifact schema 与 LLM structured outputs；本地检索层面，`BAAI/bge-m3` 与 `bge-reranker-v2-m3` 对多语言与轻量部署比较友好，适合你“本地 CPU 开发 + 4090 服务器做重实验”的现实资源。这里的强证据是官方文档；模型卡属于中等证据，足够支撑“可部署属性”判断，但不应用来吹泛化 SOTA。

## 3.8 差距分析

把当前仓库与目标系统逐项对比，结论非常明确：

* **已具备雏形的方向**：deterministic job runtime、cancel/retry/stale recovery、source policy、snapshot、claim audit、release gate 文化、phase 化 specs、phase2/3/4 测试。这个底座足够支撑企业级升级，而不是推倒重来。
* **必须彻底重写的方向**：公开服务面（HTTP API / batch / artifact viewer）、provider abstraction、connector 实现层、统一存储边界、评测平台组织方式。现状不是没有，而是边界不对、实现不够稳。
* **必须删除或归档的方向**：multi-agent graph 作为产品真相、old report-shape metrics、旧 comparator narrative、toy memory、占位型 MCP 目录。
* **必须新增的独立模块**：gateway/API、server-grade queue profile、object storage、document/evidence store、provider router、retrieval/rerank layer、observability、review surface、new evals。当前 repo 没有这些，就无法支撑“企业级可落地”叙事。
* **边界必须转向**：从“多智能体叙事”切换到“对象合同 + runtime + audit + evidence + release gate”。这不是风格偏好，而是 repo 自己未来规划与现代 Deep Research 产品形态的交集。

我的判断是：**这个仓库最正确的升级方式，不是再增强 agent graph，而是让仓库真正服从它自己在 `PLANS.md` 里提出的未来架构。**

---

# 4. 目标产品定义

## 4.1 产品一句话定义

**一个面向公司/行业深度研究的企业级 Deep Research Job System：支持异步执行、来源治理、证据优先、claim 级审计、报告包导出、可恢复运行时与 release-gated evals。**

## 4.2 用户输入 / 输出

**输入**

* 研究 brief：公司、行业、问题范围、时间窗、地域、目标输出
* source profile：`company_trusted` / `industry_broad` / `public_then_private` / `trusted_only`
* 约束：允许/拒绝域名、预算、时限、是否允许 provider-native web/file tools
* 可选文件：PDF、MD、TXT、CSV、公司材料、内部 memo

**输出**

* `report.md`
* `report.html`
* `report_bundle.json`
* `claims.json`
* `sources.json`
* `audit_decision.json`
* `trace.jsonl`
* `snapshots/`
* `manifest.json`
* 若被阻断：`review_queue.json`

## 4.3 典型流程

1. 用户提交 company/industry research brief。
2. 系统生成结构化研究计划与必答问题集。
3. 按 source policy 执行多轮 search/fetch/file ingest，写入 snapshot。
4. 从标准化文档中抽取 evidence fragments。
5. 将关键结论编成 claims，建立 support / contradiction edges。
6. 运行 audit gate；必要时继续补研，或进入人工 review。
7. 通过后综合成 report bundle，并导出 HTML/PDF/JSON。
8. 通过 API / CLI / batch 获取结果与 trace。

## 4.4 非目标

* 不是通用聊天机器人
* 不是事件抽取平台
* 不是高权限 write-back agent
* 不是“自动生成长报告即可”的文案系统
* 不是多租户 SaaS 首发版
* 不是把 provider-native deep research 直接包装一层皮

## 4.5 核心能力清单

* 异步 job lifecycle：submit / status / events / cancel / retry / resume / refine
* source governance：trusted-only、allow/deny domain、auth scope、budget
* search/fetch/file ingest 统一 connector 抽象
* snapshot + provenance + freshness metadata
* evidence fragment / claim / support-edge / conflict-set
* audit gate + review queue + override log
* report bundle + static HTML viewer + structured exports
* OpenAI / Anthropic / compatible base_url 双栈
* 本地开发 profile + 服务器实验 profile
* trust-centric evals + release gates

## 4.6 公开 surface

* **CLI**：开发、debug、复现、离线 smoke eval
* **HTTP API**：正式对外 contract
* **Batch runner**：批量研究与评测
* **Artifact viewer**：面试展示与人工 review 的静态报告界面

---

# 5. 新技术路线图

## Phase 0：真相重置与合同冻结

**目标**
把 repo 对外叙事与真实主架构统一：明确 public surface、legacy 范围、对象合同、状态语义。

**完成定义**

* 新增 ADR：`runtime-owner`、`storage-boundary`、`provider-boundary`、`audit-gate-semantics`
* 冻结核心对象：`ResearchJob / PlanStep / SourceSnapshot / EvidenceFragment / Claim / ClaimSupportEdge / ReportBundle`
* 明确 `status` 与 `audit_gate_status` 分离
* README / architecture / API readiness 更新为同一套叙事

**对 repo 的直接影响**

* 重写 README 首屏定位
* `main.py` 改成 thin wrapper
* `agents/`、`workflows/` 标注为 legacy
* 新建 `src/` 布局

**风险**
旧脚本与旧文档大量失效，短期看起来“变化很大”。

**验收方式**

* `docs/`、`specs/`、CLI `--help` 一致
* release gate 能检查 docs surface honesty
* no new feature before contracts freeze

## Phase 1：Runtime Core 提升为正式控制面

**目标**
把现有 `services/research_jobs/` 升级为核心 runtime，支持本地 profile 与 server profile。

**完成定义**

* `create / status / events / cancel / retry / resume / refine` 语义确定
* append-only event log 与 monotonic checkpoint 成为正式 contract
* 本地模式：SQLite + filesystem
* 服务模式：Postgres + Redis Streams + object store

**对 repo 的直接影响**

* `services/research_jobs/` 迁入 `src/deep_research_agent/research_jobs/`
* DB schema 与 status enum 调整
* worker lease/recovery 逻辑保留并标准化

**风险**
跨 profile 的一致性与迁移复杂度上升。

**验收方式**

* crash recovery suite 通过
* cancel/retry idempotency 通过
* SSE/event stream 可用
* 本地与服务模式跑同一任务结果 contract 一致

## Phase 2：Connector / Policy / Snapshot / Evidence 基础设施收拢

**目标**
把 search/fetch/file ingest 统一成一等 connector，并让 snapshot/evidence 成为强制路径。

**完成定义**

* 一等 connectors：web、github、arxiv、files、mcp_bridge
* `LegacyConnectorAdapter` 降为兼容层
* `snapshot_ref` 成为 evidence 前置条件
* trust taxonomy 与 source profiles 完整化
* `memory/` 重构为 document/evidence stores

**对 repo 的直接影响**

* 重写 `connectors/registry.py`
* 拆掉 `memory/store.py`
* 新增 normalization/chunking/cache 模块

**风险**
live web 抓取的不稳定会暴露更多边缘情况。

**验收方式**

* snapshot completeness ≥ 98%
* policy violation rate = 0
* trusted-only suite 通过
* file ingest suite 通过

## Phase 3：Audit 与 Report Bundle 成为一等交付物

**目标**
让系统产物从“长 Markdown 报告”升级为“可审计研究包”。

**完成定义**

* claims / support edges / conflict sets / uncertainty 全进入 bundle
* blocked critical claim 会生成 review queue
* HTML viewer 可展开 evidence anchors
* `completed` 与 `blocked review` 语义分离但同时可见

**对 repo 的直接影响**

* `auditor/` 升级
* 新建 `reporting/`
* bundle schema 稳定

**风险**
claim 粒度与 evidence linking 会产生早期噪声。

**验收方式**

* critical claim support precision 达标
* citation error rate 达标
* 100% key findings 可追到 evidence anchors
* block/review flow 可复现

## Phase 4：Provider Router + Retrieval Stack + API Surface

**目标**
补齐 OpenAI / Anthropic 双 provider、compatible base_url、server-grade API、local IR stack。

**完成定义**

* 原生 OpenAI / Anthropic adapter
* `openai_compatible` / `anthropic_compatible` profile
* provider auto/manual routing
* FastAPI API、batch API、artifact API
* 本地 embedding/rerank 服务可选开启

**对 repo 的直接影响**

* 新建 `providers/`、`gateway/`、`retrieval/`、`storage/`
* 迁移 `llm/provider.py`
* 更新配置系统

**风险**
provider feature matrix 差异会带来行为分叉。

**验收方式**

* 同一任务可切换 provider profile
* API 合同测试通过
* 本地 smoke / 服务器 full eval 都可跑

## Phase 5：Eval 平台、Release Gates、Demo Packaging

**目标**
建立正式评测面、发布闸门与面试展示资产。

**完成定义**

* `company12 / industry12 / trusted8 / file8 / recovery6 / adversarial8` 等套件落地
* GitHub Actions + nightly eval + release manifest
* 静态 demo viewer 与 architecture deck ready
* old benchmark 退为 migration diagnostics

**对 repo 的直接影响**

* `evaluation/` 重组为 `evals/`
* `scripts/` 缩减为 runner wrappers
* 新增 docs/adr 与 showcase 文档

**风险**
标注成本高、评测组织复杂。

**验收方式**

* release gates 全通过
* holdout task 与 adversarial suite 可重复
* 面试 demo 路径一键复现

---

# 6. 方法论白皮书（企业级 Deep Research Agent 方法论说明书）

下面这部分不是概念堆砌，而是后续代码与实验的直接方法学底稿。

## 6.1 问题分解方法

首先把自然语言 brief 转成一个**结构化 Research Brief Contract**，字段至少包括：

* `objective`
* `scope_entities`
* `must_answer_questions`
* `must_compare_axes`
* `time_horizon`
* `geography`
* `required_outputs`
* `source_constraints`
* `forbidden_assumptions`
* `uploaded_files`
* `decision_context`

然后做两层分解：

1. **语义分解**：让 reasoning model 产出问题树与子问题。
2. **合同校验**：deterministic validator 检查 coverage、重复、冲突与遗漏。

对“公司/行业深度研究”场景，必须强制生成以下九个研究维度，否则计划直接判不完整：

* 业务与产品
* 客户与使用场景
* GTM 与渠道
* 竞争格局
* 经济性/商业模式
* 技术与研发
* 法规/合规
* 风险与不确定性
* 需要明确承认的未知项

这一步的输出不是 prose，而是 `QuestionSet` 与 `CoverageMap`。没有 coverage，不进入下一步。

## 6.2 研究计划生成方法

研究计划不采用“agent 自由发挥”，而采用**stage-bounded plan**：

每个 `PlanStep` 至少包含：

* `step_id`
* `step_type`：scoping / official-source-discovery / primary-source-collection / contradiction-search / file-ingest / synthesis-prep
* `question_refs`
* `expected_source_types`
* `budget_slice`
* `exit_criteria`
* `fallback_strategy`
* `produces`：candidate list / source docs / evidence fragments / claims

计划不是纯 DAG，也不是纯线性列表。我的建议是：

* 外层用**有序 stage**保证生命周期可控
* 内层允许每个 stage 内部有小规模 DAG / fan-out
* collect 阶段可多轮迭代
* audit blocked 时可触发 follow-up collection，而不是整个 job 回到最初状态

## 6.3 Source Policy / Source Trust Taxonomy

source taxonomy 必须显式化，不然“citation 很多”没有意义。建议五级：

* `blocked_unsafe`：本地地址、私网地址、危险 scheme、未授权写入面
* `community_unverified`：论坛、匿名镜像、聚合站
* `secondary_reputable`：主流媒体、研究博客、咨询二手分析
* `primary_official_public`：官网、官方文档、官方 GitHub org、论文原文、监管披露
* `authenticated_or_private_primary`：上传文件、内网源、授权数据库、付费数据源

source profile 不是简单 allowlist，而是**一组策略包**：

* 允许 connectors
* 允许 trust tiers
* allow / deny domain
* auth scope
* freshness 要求
* budget cap
* source diversification 最低要求
* 是否允许 provider-native web/file tools

建议首批内置 profile：

* `company_trusted`
* `company_broad`
* `industry_trusted`
* `industry_broad`
* `public_then_private`
* `trusted_only`

默认展示场景用 `company_trusted`：先官方站、官方文档、GitHub org、监管披露、论文；再补少量高质量二手分析；论坛和社媒默认拒绝。

## 6.4 Retrieval Planning 与 Multi-query 策略

每个 `PlanStep` 不是一条 query，而是一个 query family。建议固定六类 query：

1. **entity grounding query**：确认公司/产品/部门/术语的正式名称与边界
2. **official source discovery query**：优先找官网、官方 docs、官方 repo、 filings
3. **primary evidence query**：直接面向年报、白皮书、技术文档、原文
4. **contradiction query**：主动搜反例、争议、失败案例、限制条件
5. **freshness query**：补最新变化、最近版本、最近财报、最近监管更新
6. **peer comparison query**：面向可比公司/可比赛道做横向对照

检索 ranking 不应只看 BM25/embedding 分数。推荐 composite score：

`retrieval_score = trust_weight + relevance + diversity_bonus + freshness_bonus + primary_source_bonus - duplication_penalty - policy_risk`

其中 `trust_weight` 与 `policy_risk` 是硬约束优先级，不是软参考。

## 6.5 搜索 / 抓取 / 文件接入的统一抽象

统一抽象至少分三层：

* `SearchConnector.search(request) -> CandidateSet`
* `FetchConnector.fetch(candidate) -> SourceDocument`
* `IngestConnector.ingest(file_ref) -> SourceDocument`

核心原则：

* **search 与 fetch 分离**
* **file ingest 也是 connector，不是旁路**
* **所有 document 最终都要落入统一 SourceDocument / SourceSnapshot contract**
* **任何进入 evidence 的内容必须有 snapshot_ref**

`SourceDocument` 至少包含：

* `document_id`
* `connector_name`
* `source_type`
* `canonical_uri`
* `title`
* `auth_scope`
* `published_at`
* `fetched_at`
* `freshness_metadata`
* `policy_decision`
* `snapshot_ref`

## 6.6 Snapshot / Document Normalization / Chunking / Caching

snapshot 是企业级研究系统和聊天产品的分水岭。

建议流程：

1. fetch 原文
2. 计算 `content_hash`
3. 存储 raw + text + manifest
4. 生成 `normalized_document`
5. 结构化切块并附定位信息
6. 写入 cache / embedding / rerank 索引

**Normalization**
保留标题、层级标题、段落、表格占位、页码、来源元数据、获取时间、canonical URI。

**Chunking**
采用 hybrid 策略：

* 先按结构块切：page / heading / section / list / table
* 再按 token 上限二次切分
* 每个 chunk 都保留 locator：`page`, `section`, `heading_path`, `char_span`

**Caching**
四类 cache 分开：

* search cache
* fetch cache
* embedding cache
* rerank cache

cache key 必须带版本：

`{connector}:{policy_hash}:{canonical_uri_or_query}:{content_hash}:{pipeline_version}`

## 6.7 Evidence Fragment 抽取

`EvidenceFragment` 是 claim 支撑的最小单位，不是整篇文档。

建议字段：

* `evidence_id`
* `snapshot_ref`
* `chunk_ref`
* `locator`
* `excerpt`
* `normalized_text`
* `extraction_method`
* `confidence`
* `source_trust_tier`

关键规则：

* critical claim 不能只挂“整篇文档”
* fragment 必须可反向定位
* direct quote 与 model paraphrase 分开存
* 低置信片段不得自动支撑高 criticality claim

## 6.8 Claim 建模

报告里的“关键结论”必须先成为 claim 对象，再渲染成 prose。建议 claim 类型：

* `fact`
* `comparison`
* `trend`
* `causal_hypothesis`
* `recommendation`
* `unknown_or_gap`

同时有 `criticality`：

* `low`
* `medium`
* `high`

规则：

* Executive summary、key findings、recommendations 中每个高价值句子，都要映射到一个或多个 `Claim`
* recommendation claim 的证据要求最高，必须同时有支持边与 uncertainty note
* “不知道”也是 claim，可作为 `unknown_or_gap`

## 6.9 Claim-Support-Edge / Conflict Set / Uncertainty 建模

`ClaimSupportEdge` 建议关系集：

* `supports`
* `partially_supports`
* `contradicts`
* `context_only`

每条 edge 至少有：

* `claim_id`
* `evidence_id`
* `relation`
* `confidence`
* `grounding_status`
* `rationale`

`ConflictSet` 用于把多条互相冲突的 evidence/claims 聚成一个对象，而不是在报告里悄悄压掉：

* `conflict_id`
* `claim_ids`
* `evidence_ids`
* `conflict_type`
* `summary`
* `resolution_status`

`uncertainty` 不是一句套话，而要结构化来源：

* source scarcity
* stale data
* contradictory evidence
* inferential leap
* incomplete company disclosure
* insufficient peer comparables

## 6.10 Audit Gate 设计

我建议把 audit gate 放在 **extract → claim build → support linking** 之后，synthesis 之前。

gate 判定：

* `passed`
* `blocked`
* `pending_manual_review`

关键规则：

* `status` 表示执行生命周期
* `audit_gate_status` 表示质量/审计状态
* job 可以执行完成，但仍 `audit_gate_status=blocked`
* 不再用 `needs_review` 充当生命周期终态

为什么这么做：
因为“执行结束”和“结论可信”是两件不同的事。当前仓库这两者混在一起，这是应优先修复的 contract debt。替代方案是继续保留 `needs_review` 作为 job status；不选它，因为这会让 API、监控、retry、release gate 都变脏。工程代价中等：要改状态枚举、API contract、测试与 viewer；但收益很高。对当前 repo 的改动点是 `services/research_jobs/models.py`、status 相关测试、phase04 spec、CLI 输出。

## 6.11 Synthesis / Report Bundle 设计

报告不是系统真相，**bundle 才是系统真相**。

`ReportBundle` 建议至少包含：

* `manifest`
* `job_summary`
* `key_findings`
* `claims`
* `support_edges`
* `conflicts`
* `uncertainty_notes`
* `sources`
* `audit_summary`
* `execution_summary`
* `artifacts`
* `trace_refs`

最终导出：

* Markdown：便于阅读与 Git 管理
* HTML：一等 viewer，支持展开证据
* PDF：对外分享格式，次优先级
* JSON bundle：程序消费与评测真相

HTML 结构至少要支持：

* 点击 key finding → 展开 claim
* 点击 claim → 展开 supporting evidence / contrary evidence
* 查看 snapshot metadata
* 查看 audit badge
* 查看 review notes / manual override

## 6.12 Human Review / Manual Override 设计

人工 review 不是失败补丁，而是企业级流程的一部分。

首期不做复杂前端，先做：

* CLI review command
* API review endpoint
* report viewer 中的 review-ready badge

`ReviewAction` 结构：

* `review_item_id`
* `claim_id`
* `decision`：approve / downgrade / reject / override
* `reason`
* `reviewer`
* `created_at`

规则：

* override 不能静默改历史，必须 append-only
* override 必须进入 bundle 与 trace
* 被 override 的 claim 在 viewer 里必须有显式标识

## 6.13 Provider & Model Routing 设计

provider routing 按“能力”而不是“厂商名称”做。

建议 capability tags：

* `reasoning`
* `fast_general`
* `structured_output`
* `web_search_tool`
* `file_understanding`
* `judge_quality`
* `long_context`

路由规则分两层：

**手动路由**
用户/API 指定 `provider_profile` 与 `model_profile`

**自动路由**
router 根据任务角色、预算、source profile、可用性、失败率、速率限制自动选择

角色分配原则：

* planning / decomposition：高推理模型
* extraction / query rewrite：便宜且稳的结构化模型
* synthesis：中高质量模型
* judge：最好跨 vendor，降低相关偏差
* embedding / rerank：尽量本地
* OCR / PDF hard case：provider-native file/PDF 能力仅作 fallback

为什么这么做：
这与 OpenAI 官方“planner + workhorse”的实践一致，也能避免把整个系统绑死在单个闭源 API 上。替代方案是“一把梭地所有任务都打到最强模型”；不选，因为成本高、可控性差、无法体现工程设计。工程代价中等偏高，需要 provider capability registry 与 call record。对当前 repo 的改动点主要是 `llm/provider.py`、`configs/settings.py` 和所有直接调用 LLM 的模块。

## 6.14 Runtime Reliability 设计

可靠性原则：

* 每个 stage 结束必须写 checkpoint
* 外部副作用要有 idempotency key
* worker 有 lease 与 heartbeat
* cancel / retry / resume / refine 都必须 append event
* stale job recovery 是正式能力，不是补丁
* provider / connector 失败按 error class 分层重试
* 每个 job 都有 budget ledger

`refine` 的语义建议做成：
**不是在运行中的 LLM loop 内直接改 prompt**，而是在安全边界追加一个 `refinement event`，生成新 attempt 或从下一 stage 恢复。

## 6.15 Observability / Trace / Metrics 设计

trace 层级建议：

* `job`

  * `stage`

    * `connector_call`
    * `provider_call`
    * `audit_decision`
    * `artifact_compile`

必须记录的维度：

* `job_id`, `attempt`, `stage`, `source_profile`
* `provider`, `model`, `base_url_profile`
* `connector`, `policy_decision`
* `audit_gate_status`
* `cost`, `latency`, `tool_calls`
* `snapshot_count`, `evidence_count`, `claim_count`

关键指标：

* TTFF
* TTFR
* completion rate
* resume success rate
* cancel responsiveness
* connector success rate
* policy violation rate
* critical claim support precision
* citation error rate
* audit block rate
* run-to-run variance
* cost per completed job

## 6.16 Release Gate 设计

release gate 不再问“像不像报告”，而问：

* critical claim 是否真的被支持
* citation 是否能回到 snapshot fragment
* provenance 是否完整
* policy 是否被遵守
* recovery/cancel/retry 是否稳定
* adversarial suite 是否通过
* latency / cost 是否在预算内
* docs/public surface 是否与真实实现一致

这部分应直接继承并扩展当前 `specs/evaluation-protocol.md` 与 phase06 的精神。

---

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

---

# 8. 目录级重构方案

## 8.1 新的顶层目录树

```text
.
├── src/
│   └── deep_research_agent/
│       ├── gateway/                     # [N] API / CLI / batch / review endpoints
│       │   ├── api/
│       │   ├── cli/
│       │   └── schemas/
│       ├── research_jobs/              # [M] <= services/research_jobs/
│       │   ├── contracts/
│       │   ├── orchestration/
│       │   ├── stages/
│       │   ├── repositories/
│       │   └── worker/
│       ├── connectors/                 # [M] <= connectors/ + tools/
│       │   ├── web/
│       │   ├── github/
│       │   ├── arxiv/
│       │   ├── files/
│       │   ├── mcp_bridge/
│       │   ├── legacy_adapter/
│       │   └── registry.py
│       ├── policy/                     # [M] <= policies/ + research_policy.py
│       │   ├── profiles/
│       │   ├── trust_taxonomy.py
│       │   ├── source_policy.py
│       │   └── budget.py
│       ├── evidence_store/             # [N/M] <= memory/evidence_store.py + snapshot logic
│       │   ├── documents/
│       │   ├── snapshots/
│       │   ├── chunks/
│       │   ├── evidence/
│       │   ├── claims/
│       │   └── repositories/
│       ├── auditor/                    # [M] <= auditor/
│       │   ├── pipeline.py
│       │   ├── gates.py
│       │   ├── review.py
│       │   └── store.py
│       ├── reporting/                  # [N/M] <= artifacts/ + new report delivery
│       │   ├── bundle/
│       │   ├── compiler/
│       │   ├── templates/
│       │   └── viewer_contract/
│       ├── providers/                  # [N/M] <= llm/provider.py + configs/settings.py
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   ├── openai_compat.py
│       │   ├── anthropic_compat.py
│       │   ├── router.py
│       │   └── capabilities.py
│       ├── retrieval/                  # [N]
│       │   ├── query_planning.py
│       │   ├── embeddings.py
│       │   ├── rerank.py
│       │   └── dedupe.py
│       ├── storage/                    # [N]
│       │   ├── db/
│       │   ├── object_store/
│       │   └── migrations/
│       ├── observability/              # [N]
│       │   ├── logging.py
│       │   ├── tracing.py
│       │   └── metrics.py
│       └── common/                     # [N]
│           ├── enums.py
│           ├── errors.py
│           └── utils.py
├── evals/                              # [N/M] <= evaluation/ + scripts/
│   ├── datasets/
│   ├── rubrics/
│   ├── suites/
│   ├── runners/
│   ├── graders/
│   ├── legacy_diagnostics/
│   └── reports/
├── tests/                              # [M]
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── reliability/
│   ├── adversarial/
│   └── fixtures/
├── configs/                            # [M]
│   ├── providers/
│   ├── source_profiles/
│   ├── runtime_profiles/
│   └── release_gates/
├── docs/                               # [K/M]
│   ├── adr/
│   ├── architecture/
│   ├── methodology/
│   ├── api/
│   └── demo/
├── scripts/                            # [M] thin wrappers only
├── legacy/                             # [A]
│   ├── agents/
│   ├── workflows/
│   ├── comparator/
│   ├── old_metrics/
│   └── migration_fixtures/
├── main.py                             # [M] thin wrapper to src CLI
└── pyproject.toml                      # [M]
```

## 8.2 各目录职责与迁移来源

* **保留目录**：`docs/adr`、`configs/`、`tests/` 的文化与大部分内容保留，但重排结构。
* **搬迁目录**：

  * `services/research_jobs/ -> src/.../research_jobs/`
  * `connectors/ -> src/.../connectors/`
  * `policies/ -> src/.../policy/`
  * `auditor/ -> src/.../auditor/`
  * `artifacts/ -> src/.../reporting/bundle/`
  * `llm/provider.py -> src/.../providers/`
* **新增目录**：

  * `gateway/`
  * `evidence_store/`
  * `retrieval/`
  * `storage/`
  * `observability/`
  * `evals/`
* **归档目录**：

  * `agents/`
  * `workflows/`
  * `legacy/` 原有内容
  * `evaluation/comparator*`
  * `memory/store.py`
* **删除目录/文件**：

  * 不直接删除 `main.py`，先变 wrapper
  * 删除未来主路径中对 `legacy-run`、旧 metrics 的依赖

---

# 9. 关键技术选型

## 9.1 Web/API Framework：FastAPI + Uvicorn

**选它**

* async API 友好
* 类型提示 + OpenAPI 文档天然适配 contract-first
* 适合做 SSE / artifact download / review endpoints

**不选它的替代方案**

* Flask：同步思维更强，typed contract 与 async 体验不如 FastAPI
* 纯 CLI：无法承载企业级 service surface

**工程代价**
低到中等。主要是 schema、router、integration tests。

**对当前仓库意味着什么**
把 `main.py` 的控制命令迁成 `gateway/api + gateway/cli` 双入口。

## 9.2 Task / Job Orchestration：自研 deterministic runtime 为主，Redis Streams 为服务模式队列，Temporal 作为可选后端

**选它**

* 当前仓库已有 job state machine 雏形，迁移成本最低
* Redis Streams consumer groups 的“多 consumer 分摊消息并 ack”语义适合你的规模
* 本地可保留 SQLite + subprocess，服务器再启用 Redis Streams

**替代方案**

* Celery/RQ
* Temporal

**为什么不把替代方案设为主选**

* Celery/RQ 对 claim audit / checkpoint / review queue 的语义支持太弱，仍需大量自定义控制面
* Temporal 非常强，但对当前作品集/单团队部署来说引入成本偏高；它适合作为 P2/P3 可选 backend profile，而不是 day-1 必选

**工程代价**
中等偏高。需要双 profile 运行时。

**对当前仓库意味着什么**
保留 `services/research_jobs` 思路，替换存储与队列后端即可，不必推翻。

## 9.3 Storage：PostgreSQL + SQLAlchemy 2.x Async + Alembic；本地 SQLite；对象存储用 MinIO/S3-compatible

**选它**

* 结构化 job/event/checkpoint/claim/audit 非常适合 relational schema
* SQLAlchemy async 成熟，但需按 worker/request 作用域管理 session
* SQLite 继续保留本地开发便利性

**替代方案**

* 全 SQLite
* MongoDB
* 把大对象全塞数据库

**为什么不选替代方案**

* 全 SQLite 不适合服务模式并发
* MongoDB 对关系与审计查询不如 Postgres 自然
* 大对象放 DB 会污染主库、增加备份与迁移负担

**工程代价**
中等。需要 migration 与 repository 重写。

**对当前仓库意味着什么**
`job_events/job_checkpoints` 保留思想，搬到 Postgres；`snapshots/bundles` 迁到 object store。

## 9.4 Queue：Redis Streams

**选它**

* consumer groups、subset delivery、ack 语义适合中等规模 worker pool
* 运维成本明显低于 Kafka
* 单机/单服务器环境足够实用

**不选它的替代方案**

* Kafka：过重
* RabbitMQ：也可用，但对 stream/history/consumer lag 这类场景不如 Redis Streams 自然
* 纯 DB polling：可用但不优雅

**工程代价**
中等。需要 pending/claim/retry 语义与监控。

**对当前仓库意味着什么**
worker 从 `subprocess.Popen` 升级为真正可水平扩展的 queue consumer。

## 9.5 Retrieval / Rerank / Embedding：BGE-M3 + BGE-reranker-v2-m3，本地优先

**选它**

* `bge-m3` 强调多语言、多粒度与多检索功能
* `bge-reranker-v2-m3` 轻量、易部署、适合你服务器资源
* 对中文与中英混合 company/industry research 更友好

**替代方案**

* 全部使用 provider-native embeddings/rerank
* 上大型本地 reranker/embedding stack
* 独立向量数据库即刻上马

**为什么不选替代方案**

* 全 provider-native 会加深 vendor lock-in
* 大模型本地推理不适合你本地开发机
* 独立向量库 day-1 运维成本不划算

**工程代价**
中等。需要 retrieval service 与缓存。

**对当前仓库意味着什么**
新增 `retrieval/` 层；benchmark 里可直接做 ablation：有/无 reranker。

## 9.6 Config：Pydantic Settings + YAML Profiles

**选它**

* 当前 repo 已有 `pydantic-settings` 与 YAML source profiles 文化
* 适合 provider/runtime/source/release 多 profile 管理
* Pydantic 可顺带产出 JSON Schema，用于 API contract 与 artifact validation

**替代方案**

* Hydra
* Dynaconf
* 手写 env 解析

**为什么不选替代方案**

* Hydra 太偏实验编排，学习与使用负担更高
* 手写配置会让 contract 漏洞增多

**工程代价**
低。

**对当前仓库意味着什么**
沿用现有 profile 思路，但扩展到 provider/runtime/storage/eval 全面配置。

## 9.7 Logging / Tracing / Metrics：标准 logging + JSON formatter + OpenTelemetry + Prometheus，Phoenix 可选

**选它**

* OTel 是 vendor-neutral 标准，适合 traces / metrics / logs
* Phoenix 作为本地/OSS LLM tracing 与 evaluation 界面可选，不作为强依赖

**替代方案**

* 继续以 Loguru 为中心
* 直接绑定商用平台

**为什么不选替代方案**

* Loguru 更适合单体项目，不适合作为企业级标准观测面核心
* 直接绑定商用平台不利于作品集可迁移性

**工程代价**
中等。

**对当前仓库意味着什么**
逐步从 ad-hoc logging 迁到 structured logs + traces。

## 9.8 Schema / Validation：Pydantic v2 + jsonschema

**选它**

* 统一 API input/output、bundle schema、LLM structured output
* JSON Schema 可驱动前端 viewer、artifact validation、contract tests

**替代方案**

* dataclasses + 手写校验
* Marshmallow

**为什么不选替代方案**

* 无法像 Pydantic 一样同时覆盖运行时校验、Schema 生成与类型提示体验

**工程代价**
低。

**对当前仓库意味着什么**
把 `schemas/`、`artifacts/schemas.py` 与 runtime contracts 合并成一套正式 schema 系统。

## 9.9 Testing：pytest + pytest-asyncio + httpx + hypothesis

**选它**

* 当前 repo 已有 pytest 文化
* async API / worker / queue / state machine 都适合 pytest 生态
* hypothesis 用于状态机与 contract property test 很有价值

**替代方案**

* unittest-only
* 只有端到端脚本，没有系统级测试层次

**为什么不选替代方案**

* 不利于快速回归与 release gate 自动化

**工程代价**
低到中等。

**对当前仓库意味着什么**
把 phase2/3/4 测试升级成正式 test pyramid 的一部分。

---

# 10. Provider / Model 策略

## 10.1 Provider 支持范围

首发必须支持四类 provider profile：

* `openai`
* `anthropic`
* `openai_compatible`
* `anthropic_compatible`

其中：

* OpenAI 走官方 SDK，支持 `base_url`
* Anthropic 走官方 SDK，支持 `ANTHROPIC_BASE_URL` / `base_url`
* 对兼容后端，用对应 compatibility adapter 封装，而不是在业务逻辑里到处 `if provider == ...`

## 10.2 自动 / 手动切换策略

**手动模式**
API/CLI 直接指定：

* `provider_profile`
* `model_profile`
* `routing_mode=manual`

适合评测、成本对照、面试演示。

**自动模式**
`routing_mode=auto` 时，router 根据：

* 任务角色
* required capabilities
* source profile
* latency/cost budget
* provider health
* recent failure rate
* rate limit

选择模型与 provider。

## 10.3 各类模型职责分配

| 任务角色                                        | 主要能力                           | 默认策略                     |
| ------------------------------------------- | ------------------------------ | ------------------------ |
| planning / decomposition                    | reasoning + structured output  | 优先高推理模型                  |
| query rewrite / extraction                  | structured output + 低成本        | 中档模型                     |
| synthesis / report writing                  | 质量与长文组织                        | 中高档模型                    |
| audit assist / contradiction classification | reasoning + careful comparison | 高推理模型                    |
| judge                                       | 独立 vendor 最优                   | 与 synthesis 反向厂商优先       |
| OCR / PDF hard cases                        | file understanding             | provider-native fallback |
| embeddings                                  | multilingual retrieval         | 本地模型                     |
| rerank                                      | multilingual rerank            | 本地模型                     |

## 10.4 避免写死在单一 API 之上的规则

1. source policy、snapshot、claim audit、report bundle、release gate 不依赖任何 provider 私有语义。
2. provider-native web/file search 只作为**可选增强**，不是唯一数据入口。
3. 所有 LLM 调用都经 `ProviderRouter` 与 `CallRecord`。
4. prompts 不得直接嵌入某家 API 的专属 tool schema。
5. judge 最好跨 vendor，减少 correlated bias。
6. 大部分检索与 rerank 在本地完成，避免“系统能力 = 某家 API 是否今天稳定”。

## 10.5 为什么不把系统建立在 provider-native Deep Research 上

* 它们适合作为能力参考与增强，但**不是你的产品控制面**
* OpenAI Background Mode 对长任务很好，但官方明确指出其轮询数据保留不兼容 ZDR，这对私有资料研究是约束
* 你需要自己的 source policy、snapshot、evidence objects、artifact manifest、review queue、release gates，这些不是 provider-native deep research 会替你做完的

---

# 11. 评测体系与实验矩阵

评测原则只有一句：**发布标准由 claim-level grounding、policy compliance、runtime controllability、recovery、cost/latency 决定，而不是 report 形状。** 这同时来自 OpenAI 官方 eval best practices 与仓库自己的 `specs/evaluation-protocol.md`。

## 11.1 基础测试层

| 套件                       | 实验目的                                          | 自变量                                    | 因变量                                     | 数据/任务来源                         | 通过标准                                       | 建议命令                                                                                |
| ------------------------ | --------------------------------------------- | -------------------------------------- | --------------------------------------- | ------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------- |
| `smoke_local`            | 验证本地 profile 基本可跑                             | provider profile, source profile       | completion, artifact presence           | 2–3 个小任务 + 小 PDF                | 100% 完成；无 orphan job                       | `python -m deep_research_agent.evals.run_suite --suite smoke_local --profile local` |
| `unit_contracts`         | 验证 contracts / validators / state transitions | schema version, status transition path | pass rate                               | fixtures                        | 100% 通过                                    | `... --suite unit_contracts`                                                        |
| `integration_connectors` | 验证 connector + policy + snapshot              | connector type, allow/deny, auth scope | snapshot completeness, policy violation | mocked web/file/github fixtures | violation = 0；snapshot completeness >= 98% | `... --suite integration_connectors`                                                |
| `e2e_api`                | 验证 submit→deliver 全链路                         | local/server profile                   | completion, TTFF, artifact consistency  | frozen snapshot tasks           | completion >= 95%                          | `... --suite e2e_api --profile server`                                              |

## 11.2 研究任务集

| 套件              | 实验目的                | 自变量                                   | 因变量                                                       | 数据/任务来源                                   | 通过标准                                              | 建议命令                                                    |
| --------------- | ------------------- | ------------------------------------- | --------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| `company12`     | 公司深度研究主任务集          | provider, reranker, source profile    | critical claim precision, citation error, completeness    | 12 个公司任务；官方站点/文档/GitHub/披露 + 冻结 snapshots | precision >= 0.85；citation error < 5%             | `... --suite company12 --profile server`                |
| `industry12`    | 行业研究与横向比较           | same                                  | conflict recall, uncertainty honesty, comparison coverage | 12 个行业任务；法规/标准/公司资料/论文                    | rubric coverage >= 80%                            | `... --suite industry12 --profile server`               |
| `trusted8`      | trusted-only 模式有效性  | source profile (`trusted` vs `broad`) | policy compliance, support coverage                       | 8 个 company/industry 任务                   | policy violation = 0；coverage 不低于 broad 模式 15% 以上 | `... --suite trusted8 --source-profile company_trusted` |
| `file8`         | file ingest 与公私混合研究 | file type, ingest path                | extraction quality, provenance completeness               | PDF/MD/TXT + 公网数据                         | provenance completeness >= 95%                    | `... --suite file8 --with-files`                        |
| `cross_source8` | 跨来源聚合与冲突处理          | source diversity policy               | conflict recall, contradiction handling                   | 多来源冻结快照                                   | conflict recall >= 75%                            | `... --suite cross_source8`                             |

## 11.3 可靠性 / 恢复 / 可控性

| 套件                | 实验目的                            | 自变量                         | 因变量                                 | 数据/任务来源                  | 通过标准                              | 建议命令                                          |
| ----------------- | ------------------------------- | --------------------------- | ----------------------------------- | ------------------------ | --------------------------------- | --------------------------------------------- |
| `recovery6`       | crash / stale / resume          | fault injection point       | resume success rate                 | 6 个故障注入任务                | resume success >= 90%             | `... --suite recovery6 --fault-mode injected` |
| `cancel_retry6`   | cancel/retry 语义正确性              | cancel timing, retry source | idempotency, time-to-cancel         | frozen fixtures          | cancel <= 10s；无重复 side effect     | `... --suite cancel_retry6`                   |
| `refine4`         | interrupt/refine 生效             | refine stage                | controllability score               | 4 个任务 + refine 指令        | controllability >= 80/100         | `... --suite refine4`                         |
| `stale_recovery4` | worker lease 与 pending queue 正确 | worker crash scenario       | no orphan / no duplicate processing | synthetic queue fixtures | 0 orphan；0 duplicate finalization | `... --suite stale_recovery4`                 |

## 11.4 Source Policy 与安全对抗

| 套件                         | 实验目的                                         | 自变量               | 因变量                   | 数据/任务来源                          | 通过标准                      | 建议命令                                   |
| -------------------------- | -------------------------------------------- | ----------------- | --------------------- | -------------------------------- | ------------------------- | -------------------------------------- |
| `adversarial8`             | prompt injection / mirror / stale fake-fresh | adversarial type  | adversarial pass rate | synthetic HTML/PDF/pages         | pass >= 80%               | `... --suite adversarial8`             |
| `policy_guard6`            | 网址/域名/私网/危险 scheme 拦截                        | URI type          | block accuracy        | synthetic URIs                   | 100% block expected cases | `... --suite policy_guard6`            |
| `private_public_boundary4` | 公私源隔离                                        | auth_scope mixing | leakage rate          | file + public source mixed tasks | leakage = 0               | `... --suite private_public_boundary4` |

## 11.5 质量评估

| 套件                    | 实验目的                  | 自变量                               | 因变量                                  | 数据/任务来源                  | 通过标准                                  | 建议命令                              |
| --------------------- | --------------------- | --------------------------------- | ------------------------------------ | ------------------------ | ------------------------------------- | --------------------------------- |
| `grounding_judge12`   | claim-support quality | provider, router, evidence linker | support precision, citation error    | `company12 + industry12` | precision >= 0.85；citation error < 5% | `... --suite grounding_judge12`   |
| `report_quality12`    | 报告可读性与结构              | synthesis model                   | readability, structure, rubric hints | same                     | LLM judge + human spot check 达标       | `... --suite report_quality12`    |
| `bundle_consistency8` | JSON/HTML/MD/PDF 一致性  | renderer mode                     | export consistency                   | fixed bundles            | consistency >= 99%                    | `... --suite bundle_consistency8` |

## 11.6 性能 / 成本 / 吞吐

| 套件                  | 实验目的                  | 自变量                               | 因变量                  | 数据/任务来源         | 通过标准                                    | 建议命令                                        |
| ------------------- | --------------------- | --------------------------------- | -------------------- | --------------- | --------------------------------------- | ------------------------------------------- |
| `latency_cost12`    | TTFF / TTFR / cost 控制 | provider profile, reranker on/off | TTFF, TTFR, cost/job | `company12`     | TTFF <= 120s；TTFR p50 <= 20m；p95 <= 30m | `... --suite latency_cost12`                |
| `throughput_server` | 批处理吞吐                 | worker count                      | jobs/hour, queue lag | synthetic batch | queue lag 稳定；无 stuck jobs               | `... --suite throughput_server --workers 4` |

## 11.7 Ablation Matrix

| Ablation                              | 目的                      | 自变量                     | 关键因变量                               | 通过标准              |
| ------------------------------------- | ----------------------- | ----------------------- | ----------------------------------- | ----------------- |
| `no_reranker`                         | 验证 rerank 价值            | reranker off            | support precision, completion       | 不允许显著劣化 > 10%     |
| `no_claim_audit`                      | 验证 audit gate 价值        | audit off               | citation error, unsupported leakage | 应显著变差，证明 gate 必要  |
| `no_snapshot_required`                | 验证 snapshot 强制价值        | snapshot optional       | provenance completeness             | 应显著变差             |
| `no_contradiction_queries`            | 验证反证查询价值                | contradiction query off | conflict recall                     | recall 显著下降       |
| `broad_vs_trusted`                    | 验证 trusted-only 模式成本/收益 | source profile          | policy compliance, coverage         | trusted 模式 0 违规   |
| `single_vendor_vs_cross_vendor_judge` | 验证 judge 去相关偏差          | judge strategy          | judge-human agreement               | cross-vendor 不得更差 |

## 11.8 Release Gate 检查项

正式 release gate 至少包含：

* runtime job recovery
* connector fetch security
* snapshot completeness
* claim audit grounding
* report bundle schema
* docs/public surface honesty
* API contract tests
* `company12` / `industry12` / `adversarial8` / `recovery6`
* cost/latency budget
* run-to-run variance

---

# 12. 验收标准

## P0（必须完成，未达标不应停止）

* 有正式 `POST/GET/cancel/retry/resume/refine` API
* deterministic runtime 取代旧 graph 成为唯一控制面
* `status` 与 `audit_gate_status` 分离
* web/github/arxiv/files connectors 走统一 contract
* source policy / budget / snapshot 全生效
* claim graph / support edges / review queue / blocked gate 可见
* report bundle / HTML viewer / JSON artifact 可导出
* OpenAI + Anthropic + compatible base_url 可切换
* unit / integration / e2e / recovery / adversarial 套件通过
* release gate 使用 claim-centric 指标，而不是 report-shape 指标

## P1（强烈建议完成）

* server profile：Postgres + Redis Streams + object store
* local retrieval stack：embedding + rerank
* batch pipeline
* OTEL traces + Prometheus metrics
* human review API 与最小静态 review 界面
* `company12 / industry12 / trusted8 / file8` 评测集稳定

## P2（上限增强项）

* MCP bridge
* Temporal backend profile
* 多租户 auth skeleton
* richer artifact diff / compare viewer
* scheduled research runs
* enterprise connector pack（如内部知识库、Notion、Drive 等）

**停止条件**
只要 P0 未达标，就不应把项目当“企业级 Deep Research Agent”包装；只能称为“正在迁移中的 research runtime”。

---

# 13. 风险登记表

| 类别   | 风险                            | 影响              | 缓解方案                                                                       |
| ---- | ----------------------------- | --------------- | -------------------------------------------------------------------------- |
| 技术风险 | claim-evidence linking 噪声高    | 审计误判、blocked 过多 | 先做 hybrid critical granularity；引入 frozen fixtures 与人工 spot check           |
| 技术风险 | live web 不稳定                  | eval 漂移、演示失控    | 线上/线下双轨：frozen snapshots 做回归，live tasks 做挑战集                               |
| 产品风险 | 继续滑向“聊天机器人壳子”                 | 面试定位失败          | 强制以 job API、bundle、audit、viewer 为一等 surface                                |
| 产品风险 | scope 膨胀成通用平台                 | 交付迟缓            | 只做 company/industry deep research，不做 write-back、不做事件抽取                     |
| 演示风险 | 多 agent 图太炫但无实质               | 面试官认为花哨         | 主讲 runtime、source governance、audit、eval，不主讲 agent 数量                       |
| 演示风险 | live task 太慢或失败               | 演示中断            | 预先准备 frozen bundle demo + 一条 live 任务                                       |
| 资源风险 | 本地无 GPU，服务器只有 1–2 张 4090      | 重实验受限           | 本地只做开发与 smoke；服务器跑 rerank/embedding/evals；不做超大本地 LLM 依赖                    |
| 资源风险 | API 成本失控                      | 无法持续评测          | task-role routing、cheap extraction models、本地 retrieval、budget ledger       |
| 评测风险 | LLM judge 漂移                  | 指标不稳            | cross-vendor judge + human calibration + hidden holdouts                   |
| 安全风险 | 私有文件经 provider-native tool 泄漏 | 数据边界破坏          | private source 默认走自有 ingest；provider-native background/file 功能按 profile 禁用 |
| 架构风险 | 早上太多基础设施                      | 项目推进变慢          | 先双 profile：local simple / server realistic；Temporal/MCP 设为 P2              |

---

# 14. 面试 / 简历包装建议

## 14.1 最终项目如何描述

**一行版**

> 企业级 Deep Research Agent：面向公司/行业深度研究的异步研究作业系统，支持来源治理、快照留痕、claim 级证据审计、报告包导出、可恢复运行时与 release-gated evals。

**三行版**

* 把一个 LangGraph 多智能体研究 demo 重构为 deterministic job runtime
* 建立 source policy、snapshot、claim-support graph、audit gate、report bundle
* 用 company/industry task suite、recovery/adversarial evals 和 release gates 把系统做成可辩护工程项目

## 14.2 面试里该怎么讲演进逻辑

按这条线讲：

1. **起点问题**：多 agent demo 能搜能写，但不可恢复、不可审计、不可评测。
2. **关键判断**：企业级研究系统的核心不是 agent 数量，而是 runtime / evidence / audit / eval。
3. **重构动作**：把控制面移到 deterministic state machine；把 source policy、snapshot、claim graph、report bundle 提升为一等对象。
4. **结果**：系统能异步跑、能恢复、能限制来源、能解释结论、能在发布前通过可量化 gate。

这条叙事比“我做了 6 个 agent 协作”有分量得多。

## 14.3 哪些指标值得展示

优先展示：

* critical claim support precision
* citation error rate
* provenance completeness
* trusted-only mode 违规率
* resume success rate
* cancel latency
* TTFF / TTFR
* run-to-run variance
* cost per completed job

其次展示：

* source diversity
* conflict detection recall
* uncertainty honesty score

## 14.4 哪些“看起来很炫但实际减分”的点要避免

* 不要把“多少个 agent”当核心卖点
* 不要吹“自动写几十页报告”
* 不要展示 citation 数量或字数
* 不要把 provider-native deep research 套壳说成自主系统
* 不要把一个 chat UI 当成产品完成度证明
* 不要宣称“完全自动 fact-check”

---

# TASK2_SPEC
以项目根目录为起点，yaml文件在 @./.agent/context/TASK2_SPEC.yaml
