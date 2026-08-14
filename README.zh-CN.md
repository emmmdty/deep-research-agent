# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://emmmdty.github.io/deep-research-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

**Evidence-first 的多 agent 深度研究系统**：模型驱动的 planner 把研究问题分解成任务 DAG；
并行 researcher agent 通过受治理的实时 web/GitHub/arXiv 搜索，只抽取能在逐字证据中锚定的 claim；
critic 审计每条结论并综合报告 —— 每条结论都带指向冻结不可变语料库的行内编号引用；
无法证明的内容进入人工复核队列。

这个仓库只认真主张一件事，并诚实测量它：**当答案错了，你能证明吗？**

## 测量证据（live lane：真实 LLM + 真实搜索）

以下每个数字都来自 canonical scheduler-v2 agent（`src/deep_research_agent/`）已提交的真实运行，
不是 fixture 模拟。

| 实验 | 结果 | 位置 |
| --- | --- | --- |
| **GAIA 2023（20 题纯文本抽样）** | 7/20 判卷正确（35%）、5/20 精确匹配（25%）；L1 57% · L2 25% · L3 20%；约 7.1M tokens / ~$7.1 / 36 分钟 | [`gaia_real/`](./evals/reports/live_benchmarks/gaia_real/) |
| **同模型 baseline（对照组）** | 同一个模型、每题一次调用、**无工具无检索：0/20（0%）** —— 全部分数来自 agent 机制本身，而非模型能力 | [`gaia_baseline/`](./evals/reports/live_benchmarks/gaia_baseline/) |
| **成本分析** | 每道正确答案约 $1.0；**答错的题反而多烧 1.56 倍 token** —— 多花钱不买正确率，杠杆在决策质量与审计门禁 | [`cost_analysis/`](./evals/reports/live_benchmarks/cost_analysis/) |
| **引用渲染** | 全部已提交 live bundle 经确定性引用注入器重渲染：每条 supported claim（**679/679**）都可通过行内 `[n]` 引用 + 编号 `## References` 段 + 完整 `## Claim Register` 追溯（此前读者看到的报告完全没有引用） | [`citation_rendering/`](./evals/reports/citation_rendering/) |
| **BrowseComp** | 官方 1266 题分层抽样 15 题，真实运行，每题产物已提交 | [`browsecomp_real/`](./evals/reports/live_benchmarks/browsecomp_real/) |
| **头对头对比** | ours vs langchain-ai `open_deep_research` vs `gpt-researcher`，盲评 LLM judge，同一端点。第一轮落败 —— judge 明确批评我们**缺少引用**（渲染缺口，而非证据系统问题）。修复后的第二轮：`citation_accuracy` 0.0→**1.0**、`source_coverage` 0→**47–95**（对手仍为 0），judge 的引用批评消失；剩余差距是综合散文风格，已诚实记录 | [`head_to_head/`](./evals/reports/live_benchmarks/head_to_head/) · [`head_to_head_round2/`](./evals/reports/live_benchmarks/head_to_head_round2/) |
| **错误分析** | live lane 失败分类：critic 崩溃曾消灭 25% 的正确率（已修复并重测，25%→35% 且更便宜）、多跳事实、错误事实选择、图片题（纯文本管线） | [`docs/ERROR_ANALYSIS.md`](./docs/ERROR_ANALYSIS.md) |

确定性 lane（fixture 运行、0 provider token）只证明**管线正确性**，不证明答案质量 ——
completion rate: `1.0`、critical claim support precision `1.0`、policy compliance rate: `1.0`
（冻结 fixture 上的数字），由发布冒烟门禁把关（`evals/reports/phase5_local_smoke/`）。
它被刻意单独报告，绝不与 live 数字混用。
完整指标定义见 [`docs/VALUE_SCORECARD.md`](./docs/VALUE_SCORECARD.md) 与
[`docs/EXPERIMENT_SUMMARY.md`](./docs/EXPERIMENT_SUMMARY.md)。

## Benchmark 推动了哪些真实修复

live lane 不是装饰，它已经驱动了三个真实修复：

1. **Critic 崩溃** —— 5/20 题因 critic 决策过不了 schema 校验而产出空报告。修复：确定性报告
   兜底；同一 20 题重跑：+2 道正确、成本更低。
2. **引用渲染缺口** —— 头对头 judge 批评我们"缺少引用"，尽管每条 claim 都有证据锚定。新增
   `reporting/citations.py`：确定性注入器，给报告附加行内 `[n]` 引用、编号 `## References` 段
   与完整 `## Claim Register`，并在 `audit_summary.report_citation_coverage` 里做逐 bundle
   引用覆盖率审计。
3. **没有对照组实验** —— 补上同模型无-agent 的 GAIA baseline，把"模型能力"和"agent 价值"
   分开（结果：0/20 vs 7/20）。

## 架构

![Architecture overview](./docs/assets/architecture-overview.png)

| 层 | 模块 | 职责 |
| --- | --- | --- |
| Agent 角色 | `agents/` | `LLMResearchPlanner`（目标分解 + 覆盖检查）、`LLMResearcherWorker`（原生 function-calling 循环：规划查询 → 受治理工具 → 覆盖反思 → 全文读取 → 锚定 claim）、`LLMCriticWorker`（矛盾审计 + 综合） |
| 编排 | `orchestration/` | 不可变任务 DAG、有界 asyncio 调度器（≤8 worker）、类型化消息传递、分支级重试、取消 |
| 治理 | `tool_gateway/`、`policy/` | 角色白名单、预算、幂等、缓存、prompt 注入防护 |
| 证据与审计 | `auditor/`、`evidence_store/` | 带 support edge 的 claim graph、冻结 corpus manifest、人工复核队列 |
| 交付 | `reporting/` | 确定性归并 → 审计 → 引用注入 → `report_bundle.json` + `report.md/html` |
| 可靠性 | `research_jobs/`、`observability/` | checkpoint、lease、resume/retry、成本跟踪、OpenTelemetry span |
| 产品面 | `gateway/`、`product/`、`apps/gui-web/` | CLI、本地 HTTP API（SSE）、多租户产品 API、React workspace |

运行形态：`topic → planner → ResearchDAG → scheduler → 并行 researcher → critic → 审计 → bundle`。
bundle 中每条关键 claim 必须解析到冻结 corpus manifest 内的证据片段；无法验证的 claim 进入
复核队列。离线模式（`SCHEDULER_RUNTIME_MODE=offline`）切换到确定性管线，使整套运行时无需
凭据即可演示。详见 [`docs/architecture.md`](./docs/architecture.md)。

## Demo

- **在线 Demo** —— https://emmmdty.github.io/deep-research-agent/ 。头条案例是**真实在线
  agent 运行回放**（杭州→东莞三种人设）：5 个并行 researcher、39 次受治理搜索、20 次全文读取
  （含 12306 官方页面）、3 轮反思补查、261 条锚定结论、人工核验地面真值表。
- **本地** —— `npm run dev --prefix apps/demo-site`（静态、免密钥），或 `docker compose up --build`
  跑完整产品栈。

## 快速开始

```bash
uv sync --group dev
cp .env.example .env        # 离线 demo 不需要任何密钥
uv run python main.py --help
```

确定性离线模式（无需 API key、无需网络）：`submit` 会自动落到确定性的
orchestrator-v1 benchmark 管线，保证无凭据 demo 也能产出报告。

```bash
SCHEDULER_RUNTIME_MODE=offline uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted --allow-domain anthropic.com --json
```

真实 agent（LLM planner + 治理化实时搜索 + researcher/critic），需在 `.env` 配置凭据；
`submit` 默认走 canonical scheduler-v2 运行时，`--legacy` 可强制使用旧的
orchestrator-v1 管线：

```bash
SCHEDULER_RUNTIME_MODE=production uv run python main.py submit \
  --topic "What did OpenAI announce for agents in 2026?" --json
```

运行时永远不会从生产模式静默回退到离线执行。

## 当前限制

- 部署形态是小团队 Compose 栈，不是横向扩展的 SaaS control plane。
- 纯文本管线：需要读图的 GAIA 式题目是错误分析中记录在案的失败类别。
- live 对比受端点限制：当前配置的端点只服务单一模型。
- 记忆是显式 CRUD 加按主题召回；对话自动写入长期记忆是 roadmap。
- 开放 Web 搜索只能用于发现；关键 claim 仅限受治理的冻结来源（fail closed，绝不伪造证据）。

## Roadmap

- 在固定题目上做 live 预算扫描（max_tool_calls / rounds vs 准确率）。
- Tool-calling 派发（模型自主选工具）替代受治理查询循环。
- 人工复核流程支持对已交付 bundle 重新编译或显式标注。
- 带成本/质量遥测的更多 live provider 头对头。

## Repository Layout

```text
src/deep_research_agent/  canonical runtime（agents、orchestration、auditor、reporting、product）
apps/gui-web/             React 产品工作台
apps/demo-site/           静态 GitHub Pages demo（真实运行回放 + benchmark 证据）
evals/                    live lane 证据、确定性评测资产、fixtures
docs/                     reviewer 文档（架构、评测、错误分析）
scripts/                  live runner、eval、demo 数据与分析命令
legacy/                   已归档 graph-first runtime（非产品代码，只读）
```

## 相关项目与参考

- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— 本系统针对的 checkpoint/恢复与引用归属行业痛点。
- [OpenAI Deep Research / Agents SDK](https://github.com/openai/openai-agents-python) —— 子 agent 分解、工具治理。
- [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) —— planner/researcher/critic 形态；头对头比较对象。
- [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) —— 并行子问题研究；头对头比较对象。
- [STORM](https://github.com/stanford-oval/storm) —— 大纲驱动的多视角写作。
- [Model Context Protocol](https://github.com/modelcontextprotocol/modelcontextprotocol) —— 受治理工具网关借鉴的接口约定。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
