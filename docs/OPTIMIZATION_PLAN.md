# Deep Research Agent 架构评审与升级方案

> 状态：2026-08 架构评审产出。基于一次"用项目研究项目"的双轨实验：opencode 桌面调研 vs
> 项目自身 Agent 的真实调研（v1 legacy 管线 + scheduler-v2 canonical 管线各跑一遍同一主题）。
> 已修复的缺陷见 §6，待办路线图见 §7。

## 1. 项目理解：这是一个什么样的 Agent 项目

**一句话定位**：evidence-first（证据优先）的多智能体深度研究系统。Planner 把问题分解成任务
DAG，并行 researcher 执行受治理的真实网络/GitHub/arXiv 检索，只提取能用地道引用（verbatim
quote）落地的 claim，critic 审计每条 claim 并合成报告，每个结论带编号引用，无法证明的内容
进入人工复核队列。核心卖点是"错误可被证明"（when the answer is wrong, you can prove it）。

**架构分层**（与竞品最大的差异是"证据是执行契约"而非后处理装饰）：

| 层 | 模块 | 技术 |
| --- | --- | --- |
| Agent 角色 | `agents/planner|researcher|critic` | LLM 规划 + ReAct 循环 + 反射（coverage assessment）+ 跨角色 critic |
| 编排 | `orchestration/` | 不可变任务 DAG、bounded asyncio 调度器（≤8 workers）、checkpoint journal、取消/恢复 |
| 治理 | `tool_gateway/` `policy/` | 工具白名单、预算、幂等、缓存、prompt-injection 防护、SSRF |
| 证据 | `auditor/` `evidence_store/` | claim 图、冻结 corpus manifest、审计门禁、人工复核队列 |
| 交付 | `reporting/` | 确定性 reduction → 审计 → 引用注入 → `report_bundle.json` |
| 平台 | `research_jobs/` `product/` | SQLite job 存储、租户、subprocess worker、FastAPI、SSE、PostgreSQL |
| 评测 | `evals/` | GAIA/BrowseComp/DRB 适配器、故障注入、成本分析、head-to-head |

**使用的 Agent 技术清单**：plan-and-execute、multi-agent orchestration（DAG + 消息传递）、
native function calling、ReAct 循环、reflection、grounded 写作、结构化输出、prompt-injection
guardrail、checkpoint/断点恢复、RAG（embedding rerank）、tool use with governance、退化降级
（每层都有确定性 fallback）。

## 2. 双轨调研实验（用项目研究项目）

### 2.1 方法

同一研究问题（比较 OpenAI Deep Research / gpt-researcher / open_deep_research / STORM 的
六维架构差异），三条路径独立产出：

1. **opencode 桌面调研**：本会话内 WebFetch 一手来源（arXiv、官方博客、GitHub），人工整合。
2. **项目 v1 管线**：`python main.py submit` —— **发现 CLI 默认走的是 legacy orchestrator-v1**。
3. **项目 scheduler-v2 管线**：product service 的 `submit_scheduler_v2` 路径，真实 LLM + 真实搜索。

### 2.2 结果对比

| 维度 | opencode 桌面调研 | 项目 v1（CLI 默认!） | 项目 scheduler-v2 |
| --- | --- | --- | --- |
| 来源数量/质量 | 20 个一手来源（arXiv/官方博客） | 8 个（3 个博客 + Temporal 文档 + openai 403 失败） | 115 个（claim 级引用） |
| 事实准确性 | 高（数字可溯源） | 低（"GAIA 67% L3 47.6%"来自博客二手转述，未验证） | 中高（引用可回查） |
| 结构化程度 | 对比表 + 趋势 + 架构师清单 | 章节完整但大量"暂无可用信息" | 长报告，但 executive summary 被确定性重建（见 §4） |
| 覆盖率 | 覆盖 DRB/FACT/MCP/RL 趋势 | 漏掉 citation 机制、STORM 细节 | 覆盖 12+ 系统，含 Anthropic/上下文管理/并行 |
| 引用可验证性 | 全部 URL 可溯源 | 引用是编号列表，正文无 claim 级绑定 | 每条 claim 绑定 verbatim span + 编号引用 |
| 成本/耗时 | 0 token | ~5 分钟（token 未计） | 数十分钟（4 researcher 任务 × 多轮） |
| 产出缺陷 | 依赖我的先验知识 | **审计门禁误判**：把"OpenAI 403 抓取失败"写成结论、把合法 claim 判为 contradicted | 245 claims/136 critical accepted，grounding 通过 |

### 2.3 结论（对项目的直接启示）

- **scheduler-v2 管线在"证据强度"上明显优于我的桌面调研**（claim 级 verbatim grounding +
  115 来源），这是本项目的真竞争力，不是吹牛。
- **但 CLI 默认路径是 v1 遗留管线**，`runtime_path` 默认 `orchestrator-v1`，用户第一眼体验
  的是最弱的实现 —— 这是产品级缺陷（§6.0）。
- v1 的失败模式与 README 中已诚实记录的 head-to-head 缺陷一致：引用是后处理、审计是模式
  匹配而非语义验证。这证明**升级方向不是"做得更多"，而是"把 v2 证据机制变成唯一路径 +
  补语义验证"**。
- 桌面调研的优势恰好落在本项目最弱的两点：**一手来源抓取**（openai.com 403 后无回退）与
  **语义级证据验证**（引用真假没有程序化核验）。

## 3. 各 Agent 技术的实现方案与竞品对比

| 技术维度 | 本项目现状 | 竞品主流做法 | 差距/机会 |
| --- | --- | --- | --- |
| 规划 | LLM planner（2-4 objectives，opt-in `AGENT_PLANNER_ENABLED`）+ 确定性 fallback；DAG 编译 | open_deep_research 单 search agent 迭代；gpt-researcher planner-executor-publisher；STORM perspective-guided question asking + 模拟对话 | planner 默认关闭；无 effort scaling（简单查询也全量跑） |
| 编排 | 自研 typed DAG + asyncio 调度器 + checkpoint journal | LangGraph state graph + checkpointing；CrewAI Flows | 自研是差异化（类型化契约），缺的是分布式队列/横向扩展 |
| 检索/工具 | Tavily + DDG fallback、GitHub/arXiv 搜索、fetch_page（httpx，SSRF 已修）、可选 embedding rerank | OpenAI 原生浏览器工具；gpt-researcher 多检索器 + MCP；Manus computer-use | 无浏览器自动化（Playwright）、无 MCP 生态、无原生 web_search 工具 |
| 证据/引用 | **claim 级 verbatim grounding + frozen corpus + audit gate + review queue（业内独有）** | Anthropic CitationAgent（claim→citation 定位）；DRB FACT 管线（statement→URL 验证） | 竞品在 citation 验证上更深；本项目缺"引用真伪程序化核验"（quote 是否真的出现在源文档） |
| 报告合成 | critic 一次合成 + 确定性 fallback；citation 注入器 | open_deep_research 多 agent 收集 + 单次统一合成（bitter lesson）；STORM 大纲驱动 + polishing | 方向一致；executive summary 被确定性重建丢失 nuance（见 §4） |
| 成本控制 | max_tool_calls 预算、job 级缓存、幂等 | open_deep_research 显式模型路由（mini/nano 做压缩、强模型做终稿） | **无模型路由**：全部角色用同一模型，可加 tiered routing |
| 可靠性/评估 | GAIA 35%、fault-injection 15 场景、head-to-head、agent_metrics | DRB RACE 0.43-0.49（open_deep_research）；Anthropic 内部 eval + 人工抽检 | 已有很好的地基；缺 DRB 官方评测、缺引用真实性自动化评测 |
| 记忆 | checkpoint journal、tool cache、memory_v2（TTL/supersede） | Anthropic 把计划持久化到外部 memory、subagent 结果落盘 | 无跨任务记忆复用；长任务上下文无压缩 |

### 3.1 竞品地图（2026-08 快照）

- **闭源天花板**：OpenAI Deep Research（RL 训练 + 原生浏览器工具，GAIA 72.57%）、
  Perplexity DR（<3 分钟，HLE 21.1%）。
- **开源主力**：gpt-researcher（planner-executor + MCP，~$0.4/报告）、
  LangChain open_deep_research（bitter lesson 演进，DRB RACE 0.43-0.49，成本透明 $46-187/100 任务）、
  STORM/Co-STORM（学术来源，FreshWiki +25% 组织性）。
- **框架层**：LangGraph（低层原语）、AutoGen（已进 maintenance mode → Microsoft Agent Framework）、
  CrewAI（role-based + Flows）。
- **关键趋势**：RL 训练研究代理成新天花板；"移除结构"（bitter lesson）；模型原生 browsing；
  MCP 成为工具生态事实标准；**引用可验证性成为评估主战场**（DRB FACT 管线、DRB-II 人工
  rubric，最强模型满足率 <50%）；评估从 LLM-judge 走向人类专家 rubric 对齐。

## 4. 已确认的问题清单（架构评审结论）

### 4.0 产品级（最高优先）

- **[P0] CLI 默认跑 v1 遗留管线**：`main.py submit` 创建 `runtime_path="orchestrator-v1"` 的
  job，使用 legacy agents + 模式匹配 auditor；scheduler-v2 仅 product service 可达。用户第一
  印象是最弱实现。修复方向：CLI submit 默认走 scheduler-v2（保守方案：默认不改，文档明示 +
  `--runtime v2` 参数；激进方案：v1 只保留 `--legacy`）。
- **[P1] AGENT_PLANNER_ENABLED 默认 false**：产品路径默认确定性规划，LLM planner 是隐藏能力。

### 4.1 本轮已修复（见 git diff / §5）

1. **CriticDecision "unresolved" 崩溃（Critical，实证复现）**：critic 构造决策时不传
   `unresolved`，而 reducer 校验要求 `unresolved == (decision=="unresolved")`；模型归一化与
   确定性 fallback 都会产出 "unresolved" → ValidationError → critic 任务必败 → 整个 job 失败。
2. **取消状态 checkpoint 恢复损坏（High，实证复现）**：cancelled checkpoint 被当作终态恢复进
   `results`，但既不在 `failed` 也不在 `outputs` → 恢复后任务不重跑、其依赖任务永远不 ready →
   死锁 RuntimeError 或错误地报 completed。修复：cancelled 恢复为"待重跑 + 重置 attempt 预算"，
   并跳过幽灵任务 checkpoint。
3. **Planner 跨事件循环复用 httpx client（High，潜在）**：`_call_planner_in_thread` 每次在
   新线程 `asyncio.run`，但 `self._chat` 缓存了第一个 loop 绑定的 client；第二次 plan() 静默
   降级为确定性规划。且 `.result(timeout=180)` 不生效（`with` 退出时 `shutdown(wait=True)`
   阻塞到 hung call 结束）。修复：client 在线程内新建并关闭、timeout 后 `shutdown(wait=False)`。
4. **LLM 重试无退避 + 429 立即失败 + client 永不关闭（High）**：chat/chat_with_tools/tool_loop
   三次重试无间隔；429 被当成不可重试直接抛错（与常理相反）；每个任务新建 AsyncOpenAI 从不
   aclose（fd/连接泄漏）。修复：指数退避 + 抖动、429 尊重 Retry-After 后重试、owned client
   execute 后 aclose。
5. **失败工具调用被幂等记录卡死（High）**：失败的 tool 调用被 `_complete_idempotency` 记为
   completed，scheduler 重试同一任务时拿到"重复的失败信封"→ 永远无法恢复。修复：failed 结果
   走 `reset`（可重试），succeeded/denied 才 complete；测试同步更新（原测试编码了 bug 行为）。
6. **SSRF 重定向后置校验（High）**：`fetch_page` 用 `follow_redirects=True` 先抓后验，重定向
   到 169.254.169.254 等内网地址的请求已发出；`web_scraper_tool` 完全无防护且把错误文本当
   成功内容返回（会被缓存成"证据"）。修复：手动逐跳校验（每跳先验后抓）、scraper 加同一防护、
   scraper/pdf_reader 失败改为抛异常。

### 4.2 已确认但本轮未修（进入路线图）

- **[H] 证据"审计"是结构 + 模型自述，不是验证**：`support_status` 是 researcher 模型自报；
   quote 是否真的出现在源文档从未被程序化核验（auditor 只查 hash/结构）；语义 judge 从未接线。
- **[H] 生产路径不加载 SourcePolicy/BudgetGuard**：`policy/` 只被 evals 使用；生产 researcher
   硬编码 `critical_claims_allowed: True`（连 web snippet 都能支撑 critical claim）。
- **[H] 无鉴权面**：`/v1/research/jobs*` legacy API 与 `:review` 人工复核门禁完全未认证。
- **[H] 无模型路由/effort scaling**：所有角色同一模型；无便宜模型做摘要/压缩。
- **[M] 串行网络 IO**：researcher 的 4 次搜索、3 次抓取串行执行；tool_loop 并行调用实际串行。
- **[M] 无速率限制**：登录、建 run、上传、batch 全无限流；无 per-tenant 配额。
- **[M] 观测缺失**：OTEL 全部配置好（Phoenix 容器 + 环境变量）但从未调用；CostTracker 全局单例
   非线程安全、成本按 $1/M 拍脑袋、永不落盘。
- **[M] SQLite 多进程共享无 WAL**；supervisor 无异常隔离（一个坏 checkpoint 文件 crash-loop）；
  lease fencing 在 v1 热路径缺失；resume/refine 可对 RUNNING job 调用。
- **[M] 多个死代码面**：`model_runtime/`（AES-GCM 凭证注册表）未接线；`providers/clients.py`
  角色映射会损坏多轮对话；`evidence_store/` 只写不读；MinIO/Phoenix 容器是装饰。

## 5. 本轮代码变更清单

| 文件 | 变更 |
| --- | --- |
| `agents/critic.py` | CriticDecision 构造补 `unresolved` 标志；owned chat aclose |
| `orchestration/scheduler.py` | cancelled checkpoint 恢复语义修正；幽灵任务跳过；不再伪造 attempt |
| `agents/planner.py` | 线程内建 client + aclose；timeout 真实生效（shutdown(wait=False)）；凭据探测不建 client |
| `agents/llm.py` | 指数退避 + jitter + Retry-After；429 可重试；`aclose()` |
| `agents/researcher.py` | owned chat execute 后 aclose |
| `tool_gateway/gateway.py` | failed 结果 reset 幂等而非 complete |
| `tool_gateway/registry.py` | `IdempotencyStore.reset`（协议 + InMemory 实现） |
| `connectors/tools/page_fetch.py` | 手动逐跳重定向 + 每跳 SSRF 校验 + 跳数上限 |
| `connectors/tools/web_scraper.py` | SSRF 防护 + 失败抛异常（不再返回错误文本） |
| `connectors/tools/pdf_reader.py` | 失败抛异常 |
| `tests/test_tool_gateway.py` | 3 个编码了旧 bug 行为的测试改为新语义 |

验证：`ruff check .` 通过；`pytest tests/` 485 passed / 1 skipped；`main.py --help` OK。

## 6. 升级路线图（分四期）

> 状态：一期（§6.1）已于 2026-08 落地（CLI 默认 scheduler-v2 + `--legacy`、planner 默认开启、
> 引用 quote containment 审计、policy 层接线生产 gateway）；二期（§6.2）亦已落地（引用真实性
> 程序化核验、一手来源抓取、报告保留模型原文、多模态入口）；三期（§6.3）已落地（模型路由、
> 并发优化、观测接线、平台硬化非破坏部分，队列化延后单独发布）。

### 一期：让"最强实现"成为唯一默认（对齐能力基线）✅

1. **CLI submit 默认 scheduler-v2**：`main.py submit` 走 `submit_scheduler_v2`，v1 用 `--legacy`
   保留（兼容测试与 legacy bundle 读取）。✅
2. **AGENT_PLANNER_ENABLED 默认 true**（有凭据时），确定性 planner 仍是兜底。✅
3. **证据验证硬化**：auditor 增加 **quote containment 程序化校验**（span.quote 必须出现在冻结
   文档内容中，否则 downgrade）；把 `_validate_claim` 的非法 `support_status` 从静默提升
   `qualified` 改为保守 `unsupported`。✅
4. **接线 policy 层**：`build_gateway` 加载 source profile + BudgetGuard；researcher 的
   `critical_claims_allowed` 改由 connector/来源策略决定（web snippet 默认 False）。✅

### 二期：对标竞品能力（引用可验证 + 一手来源）✅

> 状态：二期已于 2026-08 落地（`9ef4be0`、`5e11dd7`、`d1a9584`、`a80662b`、`5924060`）。

5. **引用真实性核验（对标 DRB FACT / Anthropic CitationAgent）**：新增 `verify_citations` 阶段
   —— 对 critical claims 重取源页，用确定性/LLM-judge 检查"源文档是否真的支持该声明"，
   结果进入 `audit_summary` 并落盘；这是把"模型自述"变成"程序化验证"的关键一步。✅
   （`auditor/citation_verifier.py`：critical 全验 + 冻结语料免重取 + 可选 LLM judge +
   `audit_summary["citation_verification"]` + `citation_verification.json` 落盘；仅 critical 全验，
   满足 §7 分级成本要求。）
6. **一手来源抓取策略**：openai.com 等 403/反爬回退 Wayback Machine；PDF 正文解析（Grobid
   client 默认注入或 docling 真解析，修掉 mojibake）；arXiv 全文优先。✅
   （`page_fetch` 增加 `wayback_url` + 单次回退 + `via_wayback` 标记；`pdf_reader` 改为
   pypdf→PyPDF2→docling 多后端真解析 + `repair_mojibake` 确定性修复 + 移除 10k 截断；
   `fetch_page` 支持 application/pdf 直解；`arxiv_search` 输出 `fulltext_url` 指向 HTML 全文。）
7. **报告合成保留模型原文**：executive summary 不再被确定性 top-5 bullet 整体替换；改为
   "模型合成 + claim 校验"双轨，只在越界时降级。✅
   （`bundle_v2._apply_executive_summary_policy`：标记引用全部合法 → 保留模型原文；
   引用 unsupported/contradicted/未知 claim 或摘要为空 → 确定性重建；
   `audit_summary` 新增 `executive_summary_source` / `executive_summary_validation` 审计字段。）
8. **多模态入口**（图像类问题，GAIA 失败案例之一）：vision model 已配但未接线。✅
   （`agents/vision.py` VisionChat + `connectors/tools/image_reader.py` 受治理 `read_image` 工具：
   逐跳 SSRF 校验、source policy/预算门禁、OCR 全文入库；研究者规划枚举可主动选 `read_image`；
   独立审察发现的三处缺口已修复并补回归测试，见 `5924060`。）

### 三期：成本与性能（工程化）✅

> 状态：三期已于 2026-08 落地（`6a49f08` 模型路由、`6272d1f` 并发优化、`d6877ea` 平台硬化、
> `6c58926` 观测接线、`3ea0a1a` 独立审察修复——batch 认证旁路、限流桶重置绕过、
> planning 角色路由与 effort 生效）。队列化（条目 12 的 job 存储换 Redis/DB-backed 队列）
> 会改 docker-compose 拓扑，属破坏性变更，**延后单独发布**。

9. **模型路由**：按角色/阶段路由（规划、critic、终稿用强模型；摘要、压缩、rerank 摘要用
   便宜模型），引入按任务价值的分级预算（effort scaling）。✅
   （`providers/router.py` `route_for_role(role, effort=...)`：`strong_role_models`/
   `cheap_role_models` env 覆盖 → 默认 profile，`reason="role_routing:<role>:<model>"`；
   `MultiRoleWorker` 按角色注入 routed chat，researcher 按 `task.budget["effort"]` 选 tier；
   `LLMResearchPlanner` 经 router 用 planning 强模型（brief `constraints["effort"]` 贯通）；
   `ResearchPlanner` 从 `brief.constraints["effort"]`（缺省 medium）写 `max_tool_calls`+
   `effort` 进 research task budget（8/16/32，env 可覆盖）；orchestrator `_task_model`
   优先 `config_snapshot[f"{role}_model"]` 归因。注明：critic 任务同时承担报告合成
   （"终稿"），故 `strong_role_models["synthesis"]` 由 critic 角色的强模型路由覆盖；
   `cheap_role_models["summarization"/"compression"/"rerank"]` 已在 `route_for_role` 就绪，
   但当前运行时无对应 LLM 调用点（rerank 为 embedding 实现），属前向配置。）
10. **并发优化**：researcher 搜索/抓取 `asyncio.gather` 有界并发；`tool_loop` 并行 tool calls
   真正并行；verbatim span 匹配用 Aho-Corasick/索引化。✅
   （`Semaphore(2)`+`gather`，结果按 query/url 原始顺序归位——sources/claims 与串行
   逐字节一致（测试断言）；`tool_loop` 单轮并行、结果按调用顺序追加；`auditor/span_matcher.py`
   `build_verbatim_matcher`/`match_quotes`，pyahocorasick 惰性导入、缺失时回退逐条 `in`，
   语义等价有测试覆盖。）
11. **观测接线**：`configure_tracing()` 在 app/worker 启动调用；`research_span` 包 LLM/tool/
   阶段；CostTracker 改为 per-job 归因并落盘到 bundle；`/metrics` Prometheus 端点。✅
   （`research.job_id` contextvar 由编排边界设置；CostTracker `snapshot_for/reset_for` +
   可注入价格表 + 线程安全；`run_manifest["cost_metrics"]` 落盘；`/metrics` 用
   prometheus-client 惰性导入、缺包时 503；无 OTEL 端点时 tracing no-op，离线安全。）
12. **平台硬化**：SQLite WAL + foreign_keys；supervisor try/except 隔离；job 存储换 Redis/
   DB-backed 队列；per-tenant 配额与速率限制；legacy job API 加认证。✅（非破坏部分）
   （sqlite connect pragma WAL+FK；损坏 checkpoint 跳过并回退、worker 主循环异常不
   crash-loop；legacy `/v1/research/jobs*` 与 batch 端点 X-API-Key 认证 fail-closed
   （未配置 key→503、缺失/错误→401）；进程内令牌桶按 `(tenant_id, route)` 限流、
   满表只淘汰已回满桶、新 key fail closed，429+Retry-After，test mode 可注入零限流。
   **队列替换未做**：改 docker-compose 拓扑，按 §7 单独发布。）

### 四期：长期竞争壁垒 ✅

> 状态：四期已于 2026-08 落地（`9d456d3` DRB 评测与引用真实性门禁、`e566590` 跨任务记忆复用、
> `131204d` 人工抽检与 head-to-head、`1187ded` 移除结构评审 harness、`c79fbe6` 独立审察修复）。

13. **DRB（Deep Research Bench）官方评测** + 引用真实性自动化指标进 CI 门禁。✅
    （`evals/external/benchmarks/drb.py` 适配器照 facts_grounding/gaia 模式注册
    `authoritative_release_gate`；全离线 smoke 子集 + 仓库内 fixture；`scripts/run_drb_gate.py`
    聚合 `audit_summary.citation_verification` → `verified_rate = passed/(passed+failed+unresolved)`，
    分母为空确定性判 blocked；阈值/semantic_mapping 从 `drb_gate.yaml` 真实读取；
    CI `drb-gate` job 非零退出即失败（低于阈值或 smoke 未完成均失败）；
    基线 `evals/reports/drb_gate/scorecard.json` 可字节级复现；真实数据集来源/许可/获取写进
    `evals/README.md`。）
14. **跨任务记忆复用**：job 间的 memory（记忆沉淀 → 下次研究免重复搜索）。✅
    （`memory_v2/reuse.py`：MemoryRecall 前置 recall（tenant 隔离、TTL/supersede 沿用
    MemoryService 语义）+ MemoryHarvester 完成后沉淀"已验证来源"（quote 在冻结语料中逐字命中且
    citation verdict=verified 才沉淀，永不 re-verify、幂等）；researcher `_gather_queries` 命中时
    注入逐字节相同的来源并跳过覆盖查询；空 memory 输出与现状逐字节一致；编排接线在
    `agents/factory.py` + `research_jobs/orchestrator.py`，harvest 失败不阻塞 job 完成；
    记忆来源照常进冻结 corpus、照常过 quote containment 与 verify_citations——证据契约
    （契约 T14/T16）有专项测试断言。）
15. **评估对齐人类专家**：DRB-II 式 rubric + 人工抽检通道；head-to-head 常态化。✅
    （`evals/rubrics/citation_authenticity.yaml`：引用真伪/verbatim 一致性/来源质量/覆盖面，
    每维 1–5 级带锚点示例；`main.py eval human-sample`（--bundle-dir/--sample-size/--seed
    确定性抽样 → `evals/reports/human_review/<job>.md`，--import 读回评分聚合 scorecard）；
    `evals/external/head_to_head.py` 注册进 benchmark 组合，A/B 双管线标准化 scorecard，
    无凭据环境 blocked 并支持注入 fake runner；命令与节奏见 `evals/README.md`。）
16. **评估"移除结构"每季度一次**：按 bitter lesson，随模型能力重新审视哪些结构该拆
    （当前证据契约是核心竞争力，不动；动的是外围编排）。✅（季度机制已建立 + 首份评审产出）
    （`evals/ablation_removal.py` 可重复"移除→度量"harness，输出对比 scorecard
    `evals/reports/ablation_removal/quarterly_2026_08_ablation_scorecard.json`；claim graph /
    audit gate / review queue 显式标记 PROTECTED 不可消融（按 id/模块路径/语义三重守卫）；
    首份 `docs/EVALUATION_REVIEW.md`（2026-08）给出可拆/不可拆清单与理由、本轮消融结果、
    季度时间表，产物可审计可复现。）

## 7. 风险与注意事项

- 一期 1/2 会改变 CLI 默认行为，需同步 `AGENTS.md` smoke checks 与文档；
- 引用真实性核验（二期 5）会增加成本，须按 claim criticality 分级（只对 critical 全验）；
- 三期队列化会改 `docker-compose` 拓扑，属破坏性变更，单独发布；
- 保持"证据契约"不动：claim graph / audit gate / review queue 是本项目相对所有竞品的独有
  差异，任何重构不得弱化它。

## 8. 一句话总结

这个项目已经拥有业内独有的"证据契约"（claim 级 verbatim grounding + 审计门禁 + 人工复核），
真实运行证明 scheduler-v2 管线在证据强度上超过本次桌面调研；主要问题不在能力而在**默认路径、
语义验证、平台工程**三件事上 —— 把 v2 变成唯一默认、把"模型自述"升级为"程序化引用验证"、
把平台层（鉴权/限流/观测/队列）补齐，就能把"证据优先"这个故事讲成真正的竞争壁垒。
