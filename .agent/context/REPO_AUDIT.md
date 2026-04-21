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

第二类资产是**工程内核**：`services/research_jobs/`、`connectors/models.py`、`connectors/snapshot_store.py`、`policies/source_policy.py`、`policies/budget_guardrails.py`、`auditor/models.py`、`auditor/pipeline.py`、`artifacts/`。这些模块已经包含企业级系统最重要的几个关键词：state、policy、snapshot、evidence、claim、audit、bundle。它们现在还粗，但方向对。

第三类资产是**迁移诊断资产**：`evaluation/benchmarks/`、`evaluation/comparators.py`、`scripts/run_ablation.py`、`scripts/run_portfolio12_release.py`、历史输出、测试文化、ruff / pytest 配置。这些不该再主导产品架构，但非常适合在重构过程中做 regression baseline、ablation 与 interview 叙事。

## 2.4 当前技术债

第一笔技术债是**主叙事错位**。README 开头仍在用 “LangGraph-based deep research agent / multi-agent workflow” 讲项目，而 repo 自己的 `PLANS.md` 已经要求把 multi-agent graph 降级为 legacy runtime。也就是说，仓库现在“实际最有价值的东西”与“对外讲述的东西”不是同一套。对于面试项目，这会直接减分。

第二笔技术债是**provider 与数据面不完整**。`llm/provider.py` 还是 OpenAI-compatible 统一壳，Anthropic 原生能力、base_url 双栈、provider capability routing 都没有成型；`mcp_servers/` 几乎还是占位；prompt 层也很薄。仓库 metadata 仍标注为 Alpha，并且依赖里混着 `gpt-researcher`、`langgraph`、`langchain-*` 等实验性痕迹，说明核心与实验边界还未完全分离。

第三笔技术债是**状态与存储边界混乱**。`memory/evidence_store.py` 和 `memory/store.py` 代表了两套不同的“memory”想法；而企业级研究系统真正需要的不是模糊 memory，而是明确的 `job store / document store / snapshot store / evidence store / artifact store`。当前这种混合命名会让系统继续往“聊天机器人记忆”方向漂。

## 2.5 当前 repo 中值得保留 / 迁移 / 归档 / 删除的内容

**保留（Keep）**
保留 `services/research_jobs` 的作业生命周期思想与大部分事件/检查点逻辑；保留 `connectors/models.py`、`connectors/snapshot_store.py`、URI safety、`policies/` 与 `policies/source-profiles/`；保留 `auditor/models.py` 与 `auditor/pipeline.py` 的 claim/support/conflict 思想；保留 `artifacts/`、`specs/`、phase2/3/4 测试、release gate 文化；保留 `tools/web_search.py`、`tools/github_search.py`、`tools/arxiv_search.py` 作为迁移种子；保留 `main.py` 但降级为 developer/debug CLI wrapper。

**迁移（Migrate）**
把 `services/research_jobs/` 迁入新的核心 runtime 包；把 `connectors/legacy.py` 与旧 tool 调用迁成真正的一等 connector；把 `memory/evidence_store.py` 迁入统一 evidence/document store；把 `llm/provider.py` 迁为 `providers/` 目录下的多 provider 适配器；把 `evaluation/*` 与 `scripts/*` 迁成新的 `evals/` 体系；把 `research_policy.py`、`agents/researcher.py`、`agents/verifier.py` 的有效逻辑拆散回 stage executor、extractor、auditor。

**归档（Archive）**
把 `agents/`、`workflows/`、`legacy-run` 路径、旧 comparator narrative、`evaluation/metrics.py` 中的 report-shape 打分、`memory/store.py`、占位型 `mcp_servers/` 全部归入 `legacy/` 或 `evals/legacy_diagnostics/`。它们仍可保留为 migration diagnostics，但不再进入未来公开产品主线。

**删除（Delete）**
删除“把 word count / section count / keyword hit / raw citation count 当作好坏指标”的 release 判定逻辑；删除任何把多 agent 数量当核心卖点的文档与展示；删除未来核心路径中对旧 comparator 的硬依赖。这个删除不是风格调整，而是产品边界纠偏。
