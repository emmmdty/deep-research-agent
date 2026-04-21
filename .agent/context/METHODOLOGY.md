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
