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
