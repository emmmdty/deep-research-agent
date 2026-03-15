生成日期：2026-03-15  
输入范围：当前仓库已跟踪核心文件（`README.zh-CN.md`、`main.py`、`workflows/graph.py`、`workflows/states.py`、`evaluation/comparators.py`、`configs/settings.py`、`configs/default.yaml`、`docs/architecture.md`、`tests/test_public_repo_standards.py`）、当前仓库 GitHub 公共页、Gemini Deep Research 官方博客、Gemini 官方帮助页。  
是否联网：是。  
是否实际运行验证：是，但仅限本地 `ruff check .`、`pytest -q`、`main.py --help`、`scripts/run_benchmark.py --help`；未实际运行真实 research topic，未跑通外部 comparator，未验证 Gemini 产品实机能力。  
当前仓库基线说明：当前仓库是 CLI-first 的 LangGraph 研究工程，主工作流与结构化证据模型已实现；外部 comparator 多依赖配置或导入目录；`mcp_servers/`、`memory/`、`skills/` 等仍存在占位或未纳入主工作流的边界问题，不应被写成成熟产品能力。

# 当前仓库与 Gemini Deep Research 的定位差异

结论：当前仓库与 Gemini Deep Research 不是同一层面的系统。前者是**开源、CLI-first、benchmark-aware 的研究 agent 后端样板**；后者是**Gemini App 内部的订阅型产品能力**，天然依赖 Google Search、账号体系、导出能力、产品限额、移动端与 Workspace 生态。短期目标应是对齐 Gemini 在“研究 agent 核心后端能力”上的公开能力，而不是复制其完整产品形态。

## 当前仓库基线

**已验证能力**

- 已验证：主工作流存在且路由闭环成立，`Supervisor -> Planner -> Researcher -> Critic -> Writer` 已在 [`workflows/graph.py`](../../workflows/graph.py) 中实现。
- 已验证：结构化对象 `SourceRecord`、`EvidenceNote`、`RunMetrics`、`ReportArtifact` 已在 [`workflows/states.py`](../../workflows/states.py) 中定义，并被研究/写作/评测主线消费。
- 已验证：CLI 公开边界成立，不提供受支持 HTTP API；`pytest -q` 通过，`main.py --help` 与 `run_benchmark.py --help` 可运行。证据见 [`README.zh-CN.md`](../../README.zh-CN.md) 与 [`tests/test_public_repo_standards.py`](../../tests/test_public_repo_standards.py)。

**静态可见但未实跑能力**

- 静态可见但未实跑：Researcher 已支持 `web/github/arxiv` 多源采集，但本次没有实跑真实研究任务验证其覆盖质量与稳定性。证据见 [`README.zh-CN.md`](../../README.zh-CN.md) 与 [`workflows/states.py`](../../workflows/states.py)。
- 静态可见但未实跑：`gemini` comparator 路径已存在，但默认允许 `skipped`，不能视为“Gemini Deep Research 已接通”。证据见 [`evaluation/comparators.py`](../../evaluation/comparators.py)。
- 静态可见但未实跑：`LLMJudge`、`citation_accuracy`、`source_coverage`、`aspect_coverage` 已存在，但尚不构成 claim-level 的报告真实性评测闭环。证据见 [`evaluation/comparators.py`](../../evaluation/comparators.py) 与 [`evaluation/metrics.py`](../../evaluation/metrics.py)。

**依赖配置或外部环境 / 占位未接线**

- 依赖配置或外部环境：`gptr`、`odr`、`alibaba`、`gemini` comparator 大多依赖命令模板、本地 Python 环境或报告导入目录。[`evaluation/comparators.py`](../../evaluation/comparators.py)
- 占位或未接线：`mcp_servers/` 只有占位注释；`memory/`、`skills/` 虽有代码，但未进入主工作流；`configs/default.yaml` 仍保留过时 `server:` 残留。[`mcp_servers/__init__.py`](../../mcp_servers/__init__.py) [`../architecture.md`](../architecture.md) [`../../configs/default.yaml`](../../configs/default.yaml)

## Gemini Deep Research 的公开定位边界

基于 Google 官方博客与帮助页，Gemini Deep Research 的公开定位是：

- 由 Gemini App 提供的“个人 AI 研究助理”产品能力，而不是单纯的后端库或 CLI。
- 官方明确描述了：多步研究计划、用户可审阅/批准计划、持续多轮网页浏览、输出包含源链接的综合报告、支持后续追问与导出到 Google Docs。
- 官方还明确存在产品生态依赖：Google Search 作为默认来源、可选择 Gmail/Drive/NotebookLM 等来源、每日研究次数限制、Pro/Ultra 配额差异、移动端和 Workspace 可用性差异、部分视觉/音频功能与计划档位绑定。

因此，本文件后续所有“对齐 Gemini”的目标，统一限定为**研究 agent 的核心后端能力**，不包含移动端体验、Workspace 深度集成、账号体系、商业级服务能力和品牌 UI 能力。

# 能力差距矩阵

| 能力维度 | 当前仓库 | Gemini 公开能力 | 差距等级 | 实现难度 | 建议里程碑 | 量化验收指标 |
|---|---|---|---|---|---|---|
| 任务规划能力 | 已验证存在 Planner 节点，但仅静态可见，未实跑验证“规划质量”；当前也没有“用户审阅/批准计划”的显式工件。 | 官方明确：输入问题后会先生成多步研究计划，用户可以修改或批准后再执行。来源：Google 官方博客（2024-12-11）。 | 中 | 中 | M1 | 90% 标准任务能产出结构化研究计划；计划平均覆盖 3-6 个子问题；人工抽样计划可用率 ≥ 80% |
| 多轮网页检索与浏览质量 | 静态可见：`web/github/arxiv` 多源检索已接线；未实跑真实主题，未验证浏览深度与查询改写效果。 | 官方明确：系统会持续多轮搜索、基于已学到的信息发起新搜索，并在几分钟内完成研究。 | 高 | 中高 | M1-M2 | 每任务平均 3 轮以上查询改写；来源覆盖数中位数 ≥ 12；检索失败率 ≤ 10% |
| 多来源证据交叉验证 | 已有多源采集与结构化来源记录，但未见显式 cross-source corroboration 机制；当前更像“收集后总结”。 | 官方仅明确“跨网页分析相关信息”；是否做显式交叉验证、冲突消解与 source ranking 未公开，标记为未知/未验证。 | 中高 | 中 | M2 | 抽样 claim 中至少 70% 由 2 个以上独立来源支撑；冲突来源显式标注率 ≥ 80% |
| 长报告生成与结构化引用 | 已验证：`Writer` 会输出结构化报告和引用表；但当前 `citation_accuracy` 只是引用标记 proxy，不是真实引用正确率。 | 官方明确：生成综合、易读的报告，含原始来源链接，并可导出到 Google Docs。Ultra 还可能包含视觉元素，但这属于产品生态能力。 | 中 | 中 | M2 | 报告完整度 ≥ 85%；来源链接覆盖率 ≥ 95%；引用正确率（claim-to-source 对齐）≥ 75% |
| 反思与补充研究 | 已验证：Critic 可驱动补充搜索，`follow_up_queries` 已进入主流程；但未验证真实触发质量。 | 官方明确：研究过程中会根据已学到的信息持续 refinement；完成后还支持 follow-up questions 来继续完善报告。 | 中 | 中 | M1 | 触发补充研究的任务中，二轮后质量分提升 ≥ 15%；无效补充查询比例 ≤ 20% |
| 事实一致性 | 静态可见：有 `LLMJudge` 与基础 metrics，但没有 cited/uncited claim 分离验证，也没有公开 factual benchmark 结果。 | 官方声称 2.5 Pro 下 analytical reasoning、information synthesis、report quality 提升；但没有公开事实一致性 benchmark 分数，标记为部分公开、严格量化未知。 | 高 | 高 | M2-M3 | cited claim alignment ≥ 75%；non-cited factual accuracy ≥ 80%；明显事实冲突率 ≤ 5% |
| 速度 / 成本 / 稳定性 | 已验证：有 `RunMetrics` 和成本统计结构；未实跑真实任务，因此平均耗时/成本/成功率暂无可靠基线。 | 官方公开叙事为“小时级研究压缩到分钟级”，且存在按计划档位区分的每日限制；未公开稳定延迟、成本或失败率。 | 高 | 高 | M3 | 标准任务成功率 ≥ 85%；平均耗时 ≤ 6 分钟；平均成本 ≤ \$0.60；连续 benchmark 回归失败率 ≤ 10% |
| benchmark 与评测闭环 | 已验证：有 comparator harness、离线比较与 `LLMJudge`；但没有对外稳定 benchmark 数据集、结果 schema 与公开分数。 | 官方仅公开内部偏好测试：在其测试中，2.5 Pro 驱动的 Deep Research 报告相对“其他 leading providers”获得 2:1 偏好；无可复现公开 benchmark/分数。 | 中高 | 中 | M3 | 建立冻结 benchmark 子集（20-30 题）；每次回归输出 JSONL 结果；发布公开 baseline 成绩与变更日志 |
| 研究过程可追溯性 | 已有 `EvidenceNote`、`RunMetrics`、`ReportArtifact`，但缺统一 manifest、trace export、失败 taxonomy。 | 官方公开面只说明可找回过去报告、可导出/分享/复制；内部 trace 机制未知/未验证。 | 中 | 中 | M2 | 每次运行都产出 manifest；关键步骤 trace 完整率 ≥ 95%；失败原因分类覆盖率 ≥ 90% |

说明：

- 上表中的“Gemini 公开能力”仅来自 Google 官方博客与官方帮助页；凡没有公开证据支撑的能力，一律标记为“未知/未验证”。
- “差距等级”衡量的是**研究 agent 核心后端能力**差距，不包括移动端体验、品牌 UI 或账号生态差距。

# 短期可达能力

以下项目限定为 6 个月内、基于当前仓库结构可演进实现、且不依赖 Google 级产品生态的能力。

## 1. 可审计的研究计划工件

- 目标：把 Planner 的输出从“流程内部状态”升级为显式工件，允许 CLI 下展示、复用、记录。
- 原因：Gemini 公开能力里最明确的差异之一就是“先生成计划，再执行研究”。
- 近期实现方式：
  - 固化 `TaskItem` 输出格式
  - 生成 `plan artifact`
  - 为 benchmark 保存计划工件
- 验收：
  - 90% benchmark 任务都有结构化计划工件
  - 计划与最终报告主要章节的覆盖重合度 ≥ 80%

## 2. 显式的查询改写与补充研究闭环

- 目标：把当前 `Critic -> follow_up_queries -> Researcher` 的机制强化为可观测的 query reformulation 流水线。
- 原因：Gemini 官方明确强调“根据已学到的信息发起新搜索”。
- 近期实现方式：
  - 保存每轮查询、改写原因、改写后结果
  - 统计每轮新增来源和新增证据
- 验收：
  - 至少 70% 的复杂任务发生 1 次以上有效查询改写
  - 改写后新增有效来源中位数 ≥ 3

## 3. 多源证据的交叉支撑与冲突显式化

- 目标：从“多源收集”升级到“多源支撑/冲突判定”。
- 原因：当前仓库已有 `web/github/arxiv`，但没有把多源变成可验证的 cross-check。
- 近期实现方式：
  - 为每个关键 claim 绑定多个 `SourceRecord`
  - 标识互相冲突的来源与不确定结论
- 验收：
  - 关键 claim 双源以上支撑率 ≥ 70%
  - 发现来源冲突时，显式保留“不确定”标记的比例 ≥ 80%

## 4. claim-level 报告真实性评测

- 目标：把当前 `citation_accuracy` 从标记型 proxy 升级为 claim-to-source 对齐验证。
- 原因：Gemini 官方没有公开严格 factual benchmark，当前仓库要缩短差距，必须先建立自己的真实性度量。
- 近期实现方式：
  - cited claim alignment
  - non-cited factuality 抽样验证
  - reference precision/recall
- 验收：
  - cited claim alignment ≥ 75%
  - non-cited factual accuracy ≥ 80%
  - 引用错误率 ≤ 10%

## 5. 冻结 benchmark 子集与可回放结果格式

- 目标：形成稳定对比闭环，而不是只靠脚本跑一次。
- 原因：Gemini 公开面缺可复现 benchmark，当前仓库若想长期维护，必须自己补足。
- 近期实现方式：
  - 选 20-30 个固定任务
  - 每次运行产出结果 JSONL + summary 表
  - comparator 统一输出 `completed/failed/skipped`
- 验收：
  - 每次回归都能导出结果 JSONL
  - 任务成功率 ≥ 85%
  - 失败原因可分类率 ≥ 90%

## 6. 运行工件与 trace manifest

- 目标：为每次研究输出统一的 manifest，记录计划、查询轮次、来源、证据、报告、运行指标。
- 原因：这既是追赶 Gemini“多步 agent 行为”的最短路径，也是后续产品化过渡的基础。
- 验收：
  - 100% 研究运行都产出 manifest
  - manifest 包含计划、查询、来源、证据、报告、指标六类字段

# 中长期能力目标

以下项目超出 6 个月窗口，或虽可实现，但需要较大工程投入，不适合作为近期第一优先级。

## 1. 浏览/抓取抽象层

- 目标：统一 web search、page fetch、document fetch、future browser/MCP adapters。
- 价值：提升多轮研究质量，为长文档与复杂网页研究做底层准备。
- 阶段：6-12 个月。

## 2. claim graph / evidence graph 中间表示

- 目标：把最终报告拆成 claim、evidence、source、conflict 四层结构。
- 价值：更接近“深度研究后端”而不是“报告生成器”。
- 阶段：6-12 个月。

## 3. 实验登记与可观测性平台

- 目标：引入 experiment ID、trace export、历史 runs、稳定回归比较。
- 价值：支撑长期维护的 benchmark 与质量演进。
- 阶段：6-12 个月。

## 4. 内部 service layer

- 目标：不是公开 HTTP API，而是先在内部形成稳定 job / artifact / storage 抽象。
- 价值：为后续“产品化过渡”铺路。
- 阶段：9-18 个月。

## 5. 用户数据源适配层

- 目标：允许受控接入本地文档、MCP、未来企业私有知识源。
- 价值：在不复制 Gemini 生态集成的前提下，补足“研究材料多样性”。
- 阶段：9-18 个月。

# 依赖产品生态的能力边界

以下能力即便 Gemini 官方公开可用，也不应纳入当前仓库的近期目标，因为它们主要依赖产品生态，而不是研究 agent 核心后端能力。

- **移动端体验**：Gemini 官方明确覆盖 web、Android、iOS，但这属于 Gemini App 产品层，不属于当前仓库短期目标。
- **Workspace 深度集成**：官方帮助页提到 Gmail、Drive、NotebookLM 等来源，这依赖 Google 账号、权限和服务集成，不应等同为后端研究能力。
- **账号体系与配额管理**：官方帮助页明确有每日研究次数限制、Pro/Ultra 配额差异。这属于商业产品运营能力，不是当前仓库近期建设目标。
- **商业级服务能力**：高可用、SLA、统一身份、队列、审计、计费等都属于服务化能力，当前仓库不应在 6 个月目标中承诺。
- **品牌级 UI 能力**：Google Docs 导出、Audio Overviews、视觉/动画增强、移动端通知等都不应被纳入“缩短 Gemini 后端能力差距”的核心目标。

结论：近期只追赶**计划生成、多轮检索、证据交叉验证、长报告引用质量、反思补充研究、真实性评测、benchmark 闭环**这几类后端能力。

# 里程碑路线图

## M0：基线硬化（0-4 周）

- 收敛当前仓库边界：明确 CLI-first、公有入口、comparator 成熟度、占位目录边界。
- 为研究运行补齐统一工件：`plan + report + sources + evidence_notes + metrics + manifest`。
- 验收：
  - 100% 标准任务有 manifest
  - comparator 都能显式输出 `completed/failed/skipped`

## M1：规划与多轮研究增强（1-2 个月）

- 增强 Planner 输出质量与可观测性。
- 加强 `Critic -> query reformulation -> Researcher`。
- 验收：
  - 计划可用率 ≥ 80%
  - 有效查询改写率 ≥ 70%
  - 平均新增有效来源 ≥ 3

## M2：证据与真实性闭环（2-4 个月）

- 引入 claim-level 评测与多源支撑。
- 建立“引用正确率 / factual consistency / report completeness”三类核心指标。
- 验收：
  - cited claim alignment ≥ 75%
  - non-cited factual accuracy ≥ 80%
  - 报告完整度 ≥ 85%

## M3：benchmark 回归与稳定性（4-6 个月）

- 形成冻结 benchmark 子集与统一结果 schema。
- 将 comparator harness 升级为长期回归系统。
- 验收：
  - 冻结 benchmark 集合 20-30 题
  - 标准任务成功率 ≥ 85%
  - 连续两次回归结果可复现偏差 ≤ 10%

## M4：中长期产品化过渡（6-12 个月）

- 构建搜索/抓取抽象层、内部 service layer、实验登记体系。
- 验收：
  - 研究 trace 完整率 ≥ 95%
  - 内部 job 成功率 ≥ 90%
  - 平均耗时 ≤ 5 分钟

## 如果只做最关键 5 件事

按 ROI 排序：

1. **claim-level 报告真实性评测**
   - 收益：直接缩短与 Gemini“研究质量感知”的差距。
   - 依赖：来源记录、报告工件。
   - 验收：cited claim alignment ≥ 75%，non-cited factual accuracy ≥ 80%。
2. **查询改写与补充研究闭环**
   - 收益：最接近 Gemini 官方明确公开的“持续 refinement”能力。
   - 依赖：Critic 反馈与查询日志。
   - 验收：复杂任务中 70% 以上触发有效改写。
3. **冻结 benchmark 子集 + 结果 schema**
   - 收益：让进步可度量、可复现、可长期维护。
   - 依赖：统一 comparator 输出。
   - 验收：20-30 题固定 benchmark，JSONL 可稳定导出。
4. **多源交叉支撑与冲突保留**
   - 收益：提升报告可信度，而不是单纯加来源数量。
   - 依赖：SourceRecord / claim 绑定。
   - 验收：关键 claim 双源支撑率 ≥ 70%，冲突显式化率 ≥ 80%。
5. **运行工件 manifest**
   - 收益：为所有后续能力打底，成本最低，复用价值最高。
   - 依赖：无。
   - 验收：100% 研究运行都有统一 manifest。

# 量化验收指标

| 指标 | 当前基线 | 3 个月目标 | 6 个月目标 | 12 个月目标 |
|---|---:|---:|---:|---:|
| 任务成功率（标准任务） | 未验证，估 70% | 80% | 85% | 90% |
| 平均来源覆盖数 | 未验证，估 8 | 10 | 12 | 15 |
| 有效查询改写率 | 未验证，估 0% | 50% | 70% | 80% |
| cited claim alignment | 未验证，当前缺失 | 65% | 75% | 85% |
| non-cited factual accuracy | 未验证，当前缺失 | 70% | 80% | 88% |
| 报告完整度（结构+长度） | 静态可见，估 60% | 75% | 85% | 90% |
| 平均耗时 | 未验证 | ≤ 7 分钟 | ≤ 6 分钟 | ≤ 5 分钟 |
| 平均成本 | 未验证 | ≤ \$0.80 | ≤ \$0.60 | ≤ \$0.45 |
| benchmark 可复现率 | 0 | 60% | 85% | 95% |
| pytest 通过率 | 已验证 100%（34/34） | 100% | 100% | 100% |

说明：

- 上表中的“当前基线”除 `pytest` 外，多数是保守估计或当前缺失，因为本次没有实跑真实 research topic。
- Gemini 侧没有公开稳定延迟、成本、事实一致性分数，因此这些指标是**当前仓库自身演进指标**，不是 Gemini 对标分数。

# 证据与来源

## 当前仓库事实

- 公开定位与 CLI-first 边界：[`README.zh-CN.md`](../../README.zh-CN.md)；[`tests/test_public_repo_standards.py`](../../tests/test_public_repo_standards.py)
- 主流程与迭代研究：[`workflows/graph.py`](../../workflows/graph.py)
- 结构化状态与报告工件：[`workflows/states.py`](../../workflows/states.py)
- comparator 成熟度与 `gemini/skipped` 语义：[`evaluation/comparators.py`](../../evaluation/comparators.py)
- 目录职责与边界风险：[`../architecture.md`](../architecture.md)；[`../../configs/default.yaml`](../../configs/default.yaml)

## 本次实际运行验证

- `env UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` → `All checks passed!`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q` → `34 passed in 3.53s`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` → 通过
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_benchmark.py --help` → 通过

## Gemini 官方来源

- Google 官方博客（2024-12-11）：<https://blog.google/products-and-platforms/products/gemini/google-gemini-deep-research/>
  - 公开说明了：多步研究计划、用户可修改/批准、持续多轮 web browsing、生成带原始来源链接的综合报告、支持导出到 Google Docs、支持后续追问。
- Google 官方博客（2025-03-25）：<https://blog.google/products/gemini/deep-research-gemini-2-5-pro-experimental/>
  - 公开说明了：Gemini 2.5 Pro Experimental 下 Deep Research 在 Google 内部测试中相对其他 leading providers 获得 2:1 偏好；同时提到 analytical reasoning、information synthesis、report quality 提升。
- Gemini 官方帮助页：<https://support.google.com/gemini/answer/15719111?hl=en>
  - 公开说明了：Google Search 是默认来源；可加入 Gmail、Drive、NotebookLM、上传文件；存在计划档位与每日限制；支持历史报告、分享/导出/复制；部分视觉能力与计划档位绑定。

## 已确认事实

- 当前仓库已具备多智能体主流程、结构化证据模型、benchmark/comparator 骨架和 CLI 公开入口。
- 当前仓库尚未形成 claim-level 的真实性评测闭环。
- Gemini 官方明确公开了：计划生成、多轮浏览、源链接报告、导出 Docs、后续追问。

## 未验证假设

- Gemini 是否进行显式 cross-source corroboration、冲突消解与 source ranking：未公开验证。
- Gemini 在事实一致性、平均延迟、单位成本、失败率上的真实量化表现：未公开验证。
- 当前仓库静态可见的多源研究、LLMJudge、gemini comparator 是否在真实任务下稳定有效：本次未实跑验证。

## 依赖产品生态的能力边界

- 移动端体验、Workspace 深度集成、账号体系、商业级服务能力、品牌级 UI 能力、Audio Overviews、视觉/动画增强等，均不纳入近期对齐目标。

## 下一步建议

1. 先补 claim-level 评测与冻结 benchmark 子集。
2. 再增强查询改写、多源交叉支撑和运行 manifest。
3. 只有在质量与回归指标稳定后，再讨论内部 service layer，而不是直接做公开 HTTP API。

# 更新记录

| 日期 | 输入范围 | 是否联网 | 是否有实际运行验证 | 本次新增/修订重点 |
|---|---|---|---|---|
| 2026-03-15 | 当前仓库核心已跟踪文件、GitHub 公共面、Gemini 官方博客两篇、Gemini 官方帮助页 | 是 | 是（仅 `ruff check .`、`pytest -q`、CLI `--help`） | 首版 Gemini Deep Research 能力差距分析；建立长期维护文档、差距矩阵、里程碑和更新记录 |
