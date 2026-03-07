# Deep Research Agent 🔬

> 基于 LangGraph 的多智能体深度研究系统，支持迭代搜索、质量评审、自动报告生成。

## ✨ 技术亮点

- **Multi-Agent Research System** — Supervisor / Planner / Researcher / Critic / Writer 五角色协作
- **Iterative Research Loop** — Critic 质量评审驱动迭代研究，自动补充知识空白
- **MCP Tool Integration** — 可扩展的 MCP 工具集成（预留接口）
- **Autonomous Web Research** — Tavily / DuckDuckGo / arXiv / GitHub 多源搜索
- **Long-horizon Agent Planning** — LangGraph 状态图驱动的长程研究规划

## 🏗 架构

```
              ┌─────────────┐
              │  Supervisor  │
              └──────┬──────┘
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌──────────┐ ┌────────┐
    │ Planner │ │Researcher│ │ Writer │
    └────┬────┘ └────┬─────┘ └────┬───┘
         │           │            │
         │     ┌─────▼─────┐      │
         └────►│   Critic   │◄────┘
               └─────┬─────┘
                     │ (不满足 → 继续迭代)
            ┌────────▼───────┐
            │ Iterative Loop │
            └────────────────┘
```

## 📁 项目结构

```
deep-research-agent/
├── agents/              # Multi-Agent 定义
│   ├── supervisor.py    # 顶层协调
│   ├── planner.py       # 任务拆解
│   ├── researcher.py    # 搜索 + 总结
│   ├── critic.py        # 质量评审
│   └── writer.py        # 报告撰写
├── tools/               # 工具系统（6 个工具）
├── workflows/           # LangGraph 工作流
│   ├── graph.py         # 状态图定义 + 条件路由
│   └── states.py        # TypedDict 状态 schema
├── evaluation/          # 评估与 Benchmark
│   ├── metrics.py       # 基础指标（引用/来源/深度）
│   ├── llm_judge.py     # LLM-as-Judge 5 维度评分
│   ├── cost_tracker.py  # 成本追踪器
│   └── benchmarks/      # 标准测试主题集
├── llm/                 # LLM Provider 封装 + 输出清洗
├── prompts/             # 提示词模板
├── configs/             # 配置管理（.env + YAML）
├── memory/              # 研究笔记/来源/总结 持久化
├── skills/              # 可复用研究技能模板
├── scripts/             # Benchmark + 竞品对比脚本
├── tests/               # 单元测试（pytest）
├── docs/                # 架构文档 + 开发指南 + API 文档
├── examples/            # 示例脚本
├── main.py              # CLI 入口（--topic / --serve）
└── pyproject.toml       # 依赖管理
```

## 🚀 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API 密钥
```

### 3. 运行研究

```bash
# 命令行模式
uv run python main.py --topic "2024年大语言模型Agent架构的最新进展"

# 指定迭代次数
uv run python main.py --topic "RAG技术" --max-loops 2
```

### 4. 运行 Benchmark

```bash
uv run python scripts/run_benchmark.py
```

## ⚙️ 配置

支持通过 `.env` 文件配置：

| 变量                 | 说明            | 默认值         |
| -------------------- | --------------- | -------------- |
| `LLM_PROVIDER`       | LLM 提供商      | `minimax`      |
| `LLM_MODEL_NAME`     | 模型名称        | `MiniMax-M2.5` |
| `LLM_API_KEY`        | API 密钥        | -              |
| `SEARCH_BACKEND`     | 搜索后端        | `tavily`       |
| `TAVILY_API_KEY`     | Tavily API 密钥 | -              |
| `MAX_RESEARCH_LOOPS` | 最大迭代次数    | `3`            |

## 📊 Benchmark 与评估

### 基础指标

| 指标                | 说明         | 目标       |
| ------------------- | ------------ | ---------- |
| `citation_accuracy` | 引用准确率   | > 90%      |
| `source_coverage`   | 来源覆盖率   | > 5 个来源 |
| `report_depth`      | 报告深度评分 | > 0.7      |
| `word_count`        | 报告字数     | > 5000 字  |

### LLM-as-Judge 评分

使用 LLM 自动评分 5 个维度（各 1-10 分）：**内容深度** / **事实准确度** / **逻辑连贯性** / **引用质量** / **结构完整性**

```bash
# 完整评测（含 LLM Judge）
uv run python scripts/run_benchmark.py

# 快速评测（跳过 LLM Judge）
uv run python scripts/run_benchmark.py --skip-judge --max-topics 3
```

### 竞品对比

支持与 GPT Researcher 做 head-to-head A/B 盲评：

```bash
# 实时对比
uv run python scripts/compare_agents.py --topic "RAG技术的原理和应用"

# 从已有报告对比
uv run python scripts/compare_agents.py --file-a our.md --file-b gptr.md
```

## 🛠 技术栈

- **工作流引擎**: LangGraph
- **LLM 框架**: LangChain + OpenAI SDK
- **LLM 提供商**: MiniMax / DeepSeek / OpenAI（兼容格式）
- **搜索工具**: Tavily / DuckDuckGo / arXiv / GitHub
- **数据模型**: Pydantic v2
- **日志**: Loguru
- **CLI**: Rich

## 📄 License

MIT
