# Deep Research Agent 架构设计文档

## 系统架构

Deep Research Agent 是一个基于 LangGraph 的多智能体深度研究系统，采用 **Supervisor 模式** 协调五个专业 Agent 完成端到端的研究任务。

## 工作流

```
用户输入研究主题
        │
        ▼
┌──────────────┐
│  Supervisor   │  初始化研究流程
└──────┬───────┘
       ▼
┌──────────────┐
│   Planner     │  拆解主题为 3-5 个子任务（JSON 输出）
└──────┬───────┘
       ▼
┌──────────────┐
│  Researcher   │  对每个子任务执行搜索 + LLM 总结
└──────┬───────┘
       ▼
┌──────────────┐
│    Critic     │  评审研究质量（0-10 分）
└──────┬───────┘
       │
       ├── 不满足 → 生成补充查询 → 回到 Researcher（最多 3 轮）
       │
       └── 满足 →
              ▼
       ┌──────────────┐
       │    Writer     │  整合所有总结 → 结构化 Markdown 报告
       └──────┬───────┘
              ▼
         输出报告 + 保存到 workspace
```

## 核心设计决策

### 1. LangGraph TypedDict 状态

使用 `TypedDict + Annotated` 定义状态 schema，指定各字段的合并策略：
- 列表字段（`task_summaries`、`sources_gathered`）：**追加合并**
- 标量字段（`status`、`loop_count`）：**覆盖替换**

### 2. Critic 迭代循环

Critic 通过条件边实现"满足/不满足"路由：
- 不满足时回到 Researcher 执行补充搜索
- 达到最大迭代次数时**强制通过**，避免无限循环

### 3. LLM 输出清洗

MiniMax 等模型可能在输出中包含 `<think>` 思维链标签。
`llm/clean.py` 提供统一清洗，所有 Agent 节点在处理 LLM 响应时自动调用。

### 4. 工具系统

| 工具 | 用途 | 依赖 |
|------|------|------|
| `web_search` | 网络搜索 | Tavily API / DuckDuckGo |
| `web_scraper` | 网页抓取 | httpx + BeautifulSoup |
| `arxiv_search` | 论文搜索 | arxiv 库 |
| `github_search` | 仓库搜索 | GitHub REST API |
| `pdf_reader` | PDF 解析 | PyPDF2 |
| `code_executor` | 代码执行 | subprocess 沙箱 |

## 模块职责

| 模块 | 职责 |
|------|------|
| `agents/` | 5 个 Agent 节点定义（LangGraph node 函数） |
| `workflows/` | LangGraph 状态图定义 + 状态模型 |
| `tools/` | @tool 装饰器的工具函数 |
| `prompts/` | 系统提示词 + 用户提示词模板 |
| `llm/` | LLM Provider 封装 + 输出清洗 |
| `configs/` | Pydantic BaseSettings 配置管理 |
| `evaluation/` | 评估指标 + LLM Judge + 成本追踪 |
| `memory/` | 研究笔记 / 来源 / 总结 持久化 |
| `skills/` | 可复用研究技能模板 |
| `scripts/` | Benchmark 运行 + 竞品对比脚本 |
