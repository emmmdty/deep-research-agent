# 当前仓库基线判断

结论：当前仓库最准确的定位是“已经有可运行主线和 comparator/benchmark 骨架的 CLI-first 开源 v1 研究工程”，在路线目标上更适合走“先 benchmark-first，再产品化过渡”，而不是直接自称成熟 deep research 产品。

**已实现**

- 主工作流已落地：`Supervisor -> Planner -> Researcher -> Critic -> Writer`，且 Critic 可以回流 Researcher 形成迭代闭环。证据：[`workflows/graph.py`](../../workflows/graph.py) 第 73-107 行。
- 多源证据模型已落地：`SourceRecord`、`EvidenceNote`、`RunMetrics`、`ReportArtifact` 已在状态层定义并被主线使用。证据：[`workflows/states.py`](../../workflows/states.py) 第 23-71 行；[`agents/researcher.py`](../../agents/researcher.py) 第 171-214 行。
- comparator/benchmark 骨架已落地：`ours/gptr/odr/alibaba/gemini` 的 registry、统一 `ComparatorResult`、离线 `compare_agents.py`、`run_benchmark.py`、`full_comparison.py` 都已存在。证据：[`evaluation/comparators.py`](../../evaluation/comparators.py) 第 41-143 行；[`README.zh-CN.md`](../../README.zh-CN.md) 第 51-57 行。
- 当前公开定位基本克制：仓库明确写成研究工程 / 作品集项目，公开入口只有 CLI，不提供受支持 HTTP API。证据：[`README.zh-CN.md`](../../README.zh-CN.md) 第 10-19 行；[`tests/test_public_repo_standards.py`](../../tests/test_public_repo_standards.py) 第 14-28 行。

**已声明但依赖配置/外部环境**

- 外部 comparator 不是统一开箱即用能力。`gptr` 依赖隔离 Python；`odr/alibaba` 依赖命令模板或导入目录；`gemini` 默认允许 `skipped`。证据：[`evaluation/comparators.py`](../../evaluation/comparators.py) 第 98-140 行、第 193-333 行。
- 真实研究运行依赖外部 LLM 与搜索 API；`.env.example` 暴露了 Tavily、LLM Provider、外部 comparator 的环境面。证据：[`.env.example`](../../.env.example)。
- `JUDGE_MODEL`、`RESEARCH_CONCURRENCY`、`workspace_dir` 已声明，但当前主线未形成同等强度的落地证据。证据：[`configs/settings.py`](../../configs/settings.py) 第 74-143 行；[`main.py`](../../main.py) 第 63-67 行；[`evaluation/llm_judge.py`](../../evaluation/llm_judge.py) 第 93-146 行。

**占位或未接线**

- `mcp_servers/` 当前只有占位注释，没有实际接线。证据：[`mcp_servers/__init__.py`](../../mcp_servers/__init__.py) 第 1 行。
- `memory/` 和 `skills/` 有代码，但未进入 `main.py -> workflows/graph.py` 主工作流；`docs/architecture.md` 却仍把它们写成常规模块职责，这会干扰后续演进判断。证据：[`memory/store.py`](../../memory/store.py) 第 12-78 行；[`skills/benchmark_summary.py`](../../skills/benchmark_summary.py) 第 1-34 行；[`docs/architecture.md`](../architecture.md) 第 79-92 行。
- `configs/default.yaml` 仍保留 `server.host/port`，与当前 CLI-only 公开边界冲突。证据：[`configs/default.yaml`](../../configs/default.yaml) 第 47-53 行。
- `ResearchState` 与 `GraphState` 并存，`Supervisor` 也明确还是“预留扩展”，这意味着主线清楚，但边缘结构尚未完全收束。证据：[`workflows/states.py`](../../workflows/states.py) 第 84-117 行；[`agents/supervisor.py`](../../agents/supervisor.py) 第 1-28 行。

**目录结构对后续演进的影响**

- 当前主线目录是清楚的：`agents/`、`tools/`、`workflows/`、`evaluation/`、`scripts/`。
- 真正阻碍后续“产品化过渡”的，不是主流程缺失，而是边缘目录与配置面会误导实现边界：`mcp_servers/`、`memory/`、`skills/`、`server:` 配置、双轨状态模型都让“哪些是核心能力、哪些只是预留/实验件”变得不够明确。
- 公开 GitHub 面也支持“早期工程仓库”判断：仓库创建于 2026-03-07，首个 release `v0.1.0` 发布于 2026-03-11，当前公开面约 1 star / 0 forks。官方来源：<https://github.com/emmmdty/deep-research-agent> 、<https://github.com/emmmdty/deep-research-agent/releases/tag/v0.1.0>

**本轮已实际运行验证**

- `env UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`：通过
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`：`34 passed in 3.58s`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`：通过
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_benchmark.py --help`：通过
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/full_comparison.py --help`：通过
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/compare_agents.py --help`：通过

这些验证支持“CLI-first 主线可运行”，但不等于真实 research task、外部 comparator、真实 API 配置已跑通。

# 外部优秀项目对比矩阵

| 维度 | [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | [DeepResearcher](https://github.com/GAIR-NLP/DeepResearcher) | 对当前仓库的直接启发 |
|---|---|---|---|---|
| 架构 | Planner + execution agents + publisher，另有 `multi_agents/` 路线 | LangGraph 可配置实现，带 `legacy/` 路线和 LangGraph server | 面向 RL 训练的真实 web 环境框架，`ray + handler + rollout` | 当前仓库不缺“主线 workflow”，缺的是可观测的运行契约和可复现实验层 |
| 搜索 / 浏览 | Web + local docs + JS scraping + MCP client/server | 多模型、多 search API、MCP、LangGraph Studio 配置 | 真实 web search 训练环境，依赖 handler 与搜索引擎配置 | 当前仓库已实现 `web/github/arxiv`，下一步应先补 browser/document fetch 抽象，而不是直接扩更多目录 |
| 报告生成 | 长报告、导出 PDF/Word、前端展示、图片生成 | 分离 summarization / research / compression / final report 模型 | 更偏 rollout / agent policy，报告产品面弱 | 当前仓库应优先补报告 QA，不是先补 UI |
| 评测 | `evals/` 有 SimpleQA 和 hallucination eval，但不是公开 benchmark 主线 | 官方 README 直接接入 Deep Research Bench、LangSmith 数据集、公开实验结果；README 写明 2025-08-02 达到 DRB 第 6 名、分数 0.4344 | `evaluate.sh + cacluate_metrics.py` 偏训练评估，不是产品级 benchmark | 当前仓库最值得借鉴的是 ODR 的公开 benchmark 契约，以及 ReportBench / LiveDRBench 的细粒度评测 |
| 可观测性 | LangSmith tracing、前后端、Docker、docs 较完整 | LangGraph Studio + LangSmith + OAP demo | 训练日志与 rollout 输出，偏研究内部可观测 | 当前仓库只有 `cost_tracker`，需要补 trace、experiment ID、artifact manifest |
| 产品化程度 | PyPI、FastAPI、前端、Docker、文档站、MCP 生态都成熟 | 本地 API/Studio、OAP demo、配置面完整，接近“研究型产品样板” | 训练型研究仓库，不是产品 | 当前仓库的近目标应是“产品化过渡”，不是直接追平 GPT Researcher |
| GitHub 工程化 | 约 25.7k stars，活跃 release，最新 `v3.4.3` 发布于 2026-03-13 | 约 10.8k stars，活跃测试与 experiments，但暂无 GitHub release | 约 714 stars，无 release，更像论文代码库 | 当前仓库需要先建立稳定 release 节奏、公开 benchmark 结果、文档一致性 |

**补充参照为何纳入**

- [ReportBench](https://github.com/ByteDance-BandAI/ReportBench)：不是产品样本，但它直接补上了“长报告真实性与引用质量”这一当前仓库最缺的评测层。
- [LiveDRBench](https://github.com/microsoft/livedrbench)：不是报告写作 benchmark，而是“claim discovery” benchmark，适合给当前仓库补“结构化发现产物”的第二条评测线。
- [MLGym](https://github.com/facebookresearch/MLGym)：不是当前仓库近 6 个月主线，但它提醒不要把“web research/report generation agent”过度外推为“通用 AI research agent”。

# 近年论文与基准的关键启发

| 来源 | 关键启发 | 对当前仓库的可落地动作 |
|---|---|---|
| [DeepResearcher, 2504.03160](https://arxiv.org/abs/2504.03160) | 真实 web 环境训练带来的收益，不只是模型更强，而是会涌现规划、交叉验证、自我反思、无法确定时保持诚实 | 当前仓库先不做 RL；先补查询改写、交叉验证、证据不足时显式保留不确定性 |
| [Deep Research Bench, 2506.06287](https://arxiv.org/abs/2506.06287) | benchmark 要可长期比较，必须有冻结环境或可回放环境；并且要看 hallucination、tool use、forgetting 这类 trace-level 指标 | 给当前仓库新增 frozen benchmark 子集 + trace 回放工件，别只留最终 Markdown |
| [ReportBench, 2508.15804](https://arxiv.org/abs/2508.15804) | 长报告评测不能只看总分，必须拆成 related work 精度/召回、cited statement alignment、non-cited claim factuality | 当前 `citation_accuracy` 只是“带不带引用标记”的 proxy，不是真实引用正确率；应新增 claim-level verifier |
| [Survey on Evaluation of LLM-based Agents, 2503.16416](https://arxiv.org/abs/2503.16416) | agent 评测不能只看最终结果，还要看 planning、tool use、self-reflection、memory、cost、robustness | 当前仓库应从“报告级评测”升级到“过程+结果双层评测” |
| [ReSearch, 2503.19470](https://arxiv.org/abs/2503.19470) | 搜索应被视作 reasoning chain 的一部分，而不是外接检索插件 | 当前仓库下一步不是再加搜索源，而是让 `Critic -> query reformulation -> Researcher` 更显式、更可记录 |
| [MLGym, 2502.14499](https://arxiv.org/abs/2502.14499) | 环境型 benchmark 表明当前 agent 更容易优化参数和流程，不等于能做真正开放式研究创新 | 当前仓库应继续把范围限定在 web research / report generation / evaluation，不要提前扩成“通用科研 agent” |
| [LiveDRBench, 2508.04183](https://arxiv.org/abs/2508.04183) | Deep Research 可以被形式化为“claim discovery”，从而把“发现事实”与“写好报告”分开评估 | 当前仓库应引入中间表示：claim + supporting refs，而不只保存最终报告 |

一句话提炼：当前仓库最该借的不是“更复杂的 agent 图”，而是三件事：可回放 benchmark、claim-level 报告 QA、结构化 trace/claim 中间表示。

# 当前仓库差距图谱

| 差距层 | 当前状态 | 核心差距 | 对后续演进的影响 |
|---|---|---|---|
| 搜索与浏览能力 | 已实现 `web/github/arxiv` 多源采集，证据见 [`agents/researcher.py`](../../agents/researcher.py) 第 171-214 行 | 无 browser/document fetch 抽象；`mcp_servers/` 仍是占位；本地 docs 研究与 MCP 未接线 | 研究质量天花板较低，也不利于未来产品化扩展 |
| 报告真实性评测 | 已实现 [`evaluation/metrics.py`](../../evaluation/metrics.py) + `LLMJudge` | `citation_accuracy` 只是引用密度 proxy；没有 cited/uncited claim 校验；没有 citation precision/recall | 无法对外稳健宣称“报告质量提升”，也很难接公认 benchmark |
| benchmark/comparator 主线 | 已有 registry 和脚本，但外部 comparator 多依赖命令模板、导入目录或环境，见 [`evaluation/comparators.py`](../../evaluation/comparators.py) 第 243-333 行 | 缺统一 preflight、结果 schema、公开 benchmark dataset/result contract | 目前更像“能跑比较”的 harness，不是“能公开复现”的 benchmark 项目 |
| 可观测性与实验治理 | 已有成本统计 `RunMetrics` 和 `cost_tracker` | 缺 run manifest、trace、experiment ID、失败分类、结果归档 | 无法稳定做 A/B、回归、公开结果复现 |
| 目录结构与边界 | 主线目录清楚，但 `memory/`、`skills/`、`mcp_servers/`、双轨状态、`server:` 残留仍存在 | 文档把辅助模块写成正式模块职责，见 [`docs/architecture.md`](../architecture.md) 第 79-92 行；`main.py` 仍硬编码 `workspace` 输出，见 [`main.py`](../../main.py) 第 63-67 行 | 这是当前仓库向“产品化过渡”最大的结构性阻力 |
| 产品化边界 | 明确 CLI-only，见 [`README.zh-CN.md`](../../README.zh-CN.md) 第 19 行 | 没有受支持 API、异步任务、持久化、鉴权、成本限额、workspace 隔离 | 不能直接跳到“成熟产品”叙事，只能先补内部服务边界 |

# 适用于当前项目的完整迭代方案

**Phase 0：0-4 周，先收边界与测量底座**

- 能力演进：不新增受支持 HTTP API；把每次运行固定产出为 `report + sources + evidence_notes + critic_feedback + run_metrics + trace manifest`。
- 评测体系：保留现有 `LLMJudge` 和 comparator harness，但新增统一 result schema，明确 `completed/failed/skipped` 与缺失原因。
- 工程治理：收敛 `configs/default.yaml` 的 `server:` 残留，统一 `workspace_dir`/输出路径约定，明确 `mcp_servers/`、`memory/`、`skills/` 的实验/辅助属性。
- GitHub 公开面：在 README / docs 中补 comparator 能力矩阵、公开支持面、benchmark 结果格式约定。
- 阶段目标：把仓库从“能跑”提升到“结果可回放、边界可说明”。

**Phase 1：1-3 个月，先把“报告质量”变成可测量对象**

- 能力演进：在 Researcher/Critic 闭环中加入显式 query reformulation、cross-source corroboration、evidence insufficient 路径。
- 评测体系：实现 ReportBench 风格的三层评测。
  - related work / reference precision-recall
  - cited claim alignment
  - non-cited claim fact-check
- 工程治理：引入 frozen benchmark 子集，优先做 20-30 个任务的内部可回放 benchmark。
- GitHub 公开面：发布 benchmark 任务 schema、result JSONL schema、baseline result 样例。
- 阶段目标：把当前仓库从“报告生成器 + comparator harness”升级为“有可信质量度量的研究工程”。

**Phase 2：3-6 个月，做实验平台化与服务预备，而不是先做公开 API**

- 能力演进：抽象搜索/抓取层，统一 web/api/html/browser/document fetch；MCP 只有在真正接线后才进入正式主线。
- 评测体系：增加 LiveDRBench 风格的 `claim + refs` 中间表示，用来分离“发现事实”和“写好报告”。
- 工程治理：引入 experiment ID、trace export、summary CSV/JSONL、失败 taxonomy；把 `research_concurrency` 等声明型配置真正接线，或明确降级为内部预留。
- GitHub 公开面：对每次 release 附 benchmark 结果与配置说明，不再只发功能叙事。
- 阶段目标：让仓库具备“工程化研究平台”气质，而不是只是脚本集合。

**Phase 3：6-12 个月，在质量门槛达标后再做最小产品化**

- 进入条件：
  - 引用正确率 ≥ 0.80
  - 事实一致性 ≥ 0.80
  - 标准任务成功率 ≥ 0.85
  - 至少 1 个公开 benchmark 有稳定可复现成绩
- 能力演进：先做内部 SDK / service layer，再考虑最小异步 job API；若对外暴露接口，必须同时提供 auth、持久化、workspace 隔离、成本限制、trace。
- 评测体系：发布长期维护的 benchmark results 与 change log。
- GitHub 公开面：建立稳定 release 节奏与 benchmark-driven release note。
- 阶段目标：从“研究工程”平滑过渡到“有克制边界的研究型产品”。

**明确不建议作为近 6 个月主线的事项**

- 不建议优先转向 DeepResearcher / MLGym 式 RL 训练主线。
- 不建议在没有 claim-level QA 和 benchmark 契约前先做受支持 HTTP API。
- 不建议把 `mcp_servers/`、`skills/`、`memory/` 继续按已接线能力对外叙述。

# 量化指标与阶段目标

注：`实测` 为本轮命令验证结果；`估` 为基于当前代码与公开面保守估计，因为本轮没有实际跑主题研究任务、没有跑外部 comparator、也没有跑公开 benchmark。

**质量指标**

| 指标 | 当前基线 | 3 个月目标 | 6 个月目标 | 12 个月目标 |
|---|---:|---:|---:|---:|
| 引用正确率（cited claim alignment） | 估 55% | 70% | 82% | 90% |
| 来源覆盖（达到最低来源/方面要求的任务占比） | 估 35% | 60% | 75% | 85% |
| 报告完整度（满足字数+结构阈值的任务占比） | 估 60% | 75% | 85% | 90% |
| 事实一致性（抽样 claims 与来源/网络验证一致） | 估 55% | 72% | 82% | 90% |

**工程指标**

| 指标 | 当前基线 | 3 个月目标 | 6 个月目标 | 12 个月目标 |
|---|---:|---:|---:|---:|
| 任务成功率（标准任务完成率） | 估 70% | 80% | 88% | 92% |
| 平均耗时（标准任务） | 估 6.0 分钟 | 5.5 分钟 | 5.0 分钟 | 4.5 分钟 |
| 平均成本（标准任务） | 估 \$0.60 | ≤ \$0.55 | ≤ \$0.45 | ≤ \$0.35 |
| pytest 通过率 | 实测 100%（34/34） | 100% | 100% | 100% |
| CI 稳定性 | 估 80% | 90% | 95% | 98% |

**路线指标**

| 指标 | 当前基线 | 3 个月目标 | 6 个月目标 | 12 个月目标 |
|---|---|---|---|---|
| 公开 benchmark 分数/排名 | 未上榜 | 完成首个公开 benchmark 提交 | 至少 1 个公开榜单进入前 50% | 稳定进入前 30% |
| 公开 release 节奏 | 1 次公开 release（2026-03-11） | 至少每 8 周 1 次 | 至少每 6 周 1 次 | 稳定每 4-6 周 1 次 |
| 文档一致性覆盖率 | 估 65% | 85% | 95% | 98% |

**优先级前 10 的迭代 backlog**

| 优先级 | 事项 | 收益 | 依赖 | 验收标准 |
|---|---|---|---|---|
| 1 | 运行工件契约：`manifest + report + sources + judge + trace` | 所有评测、对比、回放的基础 | 无 | 每次运行都产出统一 schema；测试覆盖 schema |
| 2 | ReportBench 风格 claim verifier | 把“质量”从叙事变成指标 | 1 | 输出 cited alignment、uncited accuracy、reference precision/recall |
| 3 | DRB 风格 frozen benchmark 子集 | 让结果可长期比较 | 1 | 有 20-30 个冻结任务、baseline outputs、result JSONL |
| 4 | Comparator preflight 与能力矩阵 | 防止继续误写“全部已接通” | 无 | 每个 comparator 都能明确报 `completed/failed/skipped` 原因 |
| 5 | Query reformulation + cross-source corroboration | 提升覆盖与事实一致性 | 1,3 | trace 中能看到改写查询、交叉验证次数与失败原因 |
| 6 | 搜索/抓取抽象层 | 为 browser/MCP/local docs 扩展做准备 | 1 | 当前 `web/github/arxiv` 不回归，且新增统一 fetch 接口 |
| 7 | 收敛未接线配置与目录边界 | 降低结构噪音，便于产品化过渡 | 无 | `server:` 残留消失；`mcp_servers/`、`memory/`、`skills/` 状态明确 |
| 8 | 实验登记与 trace export | 支撑 A/B、回归、公开结果复现 | 1,3 | 每轮 benchmark 都有 experiment ID、summary CSV/JSONL |
| 9 | 公开 benchmark 发布流程 | 提升 GitHub 公开面可信度 | 2,3,8 | README/release note 附 benchmark 表格、配置、复现说明 |
| 10 | 最小 SDK / 内部 service layer | 为产品化过渡铺路 | 1,2,3,8 且质量门槛达标 | 有稳定内部接口；若暴露 HTTP，则必须含 auth、async job、trace、cost guardrail |

# 证据与来源

**本地仓库事实**

- 公开定位与 CLI 边界：[`README.zh-CN.md`](../../README.zh-CN.md) 第 8-19 行；[`main.py`](../../main.py) 第 70-99 行；[`tests/test_public_repo_standards.py`](../../tests/test_public_repo_standards.py) 第 14-44 行。
- 主流程与结构化状态：[`workflows/graph.py`](../../workflows/graph.py) 第 73-166 行；[`workflows/states.py`](../../workflows/states.py) 第 23-117 行。
- 多源采集、comparator、Judge、指标：[`agents/researcher.py`](../../agents/researcher.py) 第 171-240 行；[`evaluation/comparators.py`](../../evaluation/comparators.py) 第 41-379 行；[`evaluation/llm_judge.py`](../../evaluation/llm_judge.py) 第 93-220 行；[`evaluation/metrics.py`](../../evaluation/metrics.py) 第 1-141 行。
- 结构与边界问题：[`configs/settings.py`](../../configs/settings.py) 第 74-143 行；[`configs/default.yaml`](../../configs/default.yaml) 第 47-53 行；[`docs/architecture.md`](../architecture.md) 第 79-92 行；[`mcp_servers/__init__.py`](../../mcp_servers/__init__.py) 第 1 行；[`memory/store.py`](../../memory/store.py) 第 12-78 行；[`skills/benchmark_summary.py`](../../skills/benchmark_summary.py) 第 1-34 行。

**本轮实际运行验证**

- `env UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` → `All checks passed!`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q` → `34 passed in 3.58s`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_benchmark.py --help`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/full_comparison.py --help`
- `env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/compare_agents.py --help`

**外部官方 GitHub / 论文 / benchmark 来源**

- 当前仓库公开页与 release：<https://github.com/emmmdty/deep-research-agent> 、<https://github.com/emmmdty/deep-research-agent/releases/tag/v0.1.0>
- GPT Researcher：<https://github.com/assafelovic/gpt-researcher> 、<https://github.com/assafelovic/gpt-researcher/releases/tag/v3.4.3> 、<https://github.com/assafelovic/gpt-researcher/tree/main/evals>
- Open Deep Research：<https://github.com/langchain-ai/open_deep_research>
- DeepResearcher：<https://github.com/GAIR-NLP/DeepResearcher> 、<https://arxiv.org/abs/2504.03160>
- Deep Research Bench：<https://arxiv.org/abs/2506.06287>
- ReportBench：<https://github.com/ByteDance-BandAI/ReportBench> 、<https://arxiv.org/abs/2508.15804>
- Agent 评测综述：<https://arxiv.org/abs/2503.16416>
- ReSearch：<https://arxiv.org/abs/2503.19470>
- MLGym：<https://github.com/facebookresearch/MLGym> 、<https://arxiv.org/abs/2502.14499>
- LiveDRBench：<https://github.com/microsoft/livedrbench> 、<https://arxiv.org/abs/2508.04183>

**限制说明**

- 本轮没有实际跑真实 research topic，也没有跑通 `gptr/odr/alibaba/gemini` comparator；因此关于它们的成熟度判断，除 `--help` 与静态代码外，均不是“已跑通”结论。
- `Deep Research Bench` 的官方 leaderboard 页面在当前调研链路下未直接抓到页面快照，因此关于排行榜位置的引用采用了官方论文摘要和 LangChain 官方 README，没有把二手媒体报道当依据。
- 当前本地工作树不是完全干净；`docs/development.md`、`prompts/` 相关文件存在本地漂移。涉及“公开仓库”结论时，我优先采用 GitHub 公共页和已跟踪公开文件，不把未提交内容误当成公开事实。
