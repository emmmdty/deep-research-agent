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

使用 `TypedDict + Annotated` 定义状态 schema，并按字段职责指定合并策略：
- 研究循环中的列表字段（`task_summaries`、`sources_gathered`、`search_results`、`evidence_notes`）：**覆盖替换**
- 标量字段（`status`、`loop_count`、`final_report`）：**覆盖替换**

这样可以避免 Critic 触发多轮迭代时，旧来源和旧总结被 LangGraph reducer 重复累计。

### 2. Critic 迭代循环

Critic 通过条件边实现"满足/不满足"路由：
- 不满足时回到 Researcher 执行补充搜索
- 达到最大迭代次数时**强制通过**，避免无限循环

### 3. LLM 输出清洗

MiniMax 等模型可能在输出中包含 `<think>` 思维链标签。
`llm/clean.py` 提供统一清洗，所有 Agent 节点在处理 LLM 响应时自动调用。

### 4. 多源研究与证据模型

Researcher 不再只拼接单一搜索文本，而是按来源类型收集结构化证据：

| 组件 | 用途 | 主要产物 |
|------|------|----------|
| `web_search` | 通用网页搜索 | `SourceRecord(source_type="web")` |
| `github_search` | GitHub 仓库/代码线索 | `SourceRecord(source_type="github")` |
| `arxiv_search` | 论文搜索 | `SourceRecord(source_type="arxiv")` |
| `writer` | 统一引用编号与参考来源表 | `ReportArtifact` |
| `cost_tracker` | 记录 LLM / 搜索调用 | `RunMetrics` |

核心状态对象包括：
- `SourceRecord`：标题、URL、来源类型、查询、引用编号
- `EvidenceNote`：每轮研究总结及支撑来源编号
- `RunMetrics`：耗时、LLM 调用、搜索调用、token 与估算成本
- `ReportArtifact`：最终报告、引用表、证据表与运行指标

## 模块职责

| 模块 | 职责 |
|------|------|
| `agents/` | 5 个 Agent 节点定义（LangGraph node 函数） |
| `workflows/` | LangGraph 状态图定义 + 状态模型 |
| `tools/` | @tool 装饰器的工具函数 |
| `prompts/` | 系统提示词 + 用户提示词模板 |
| `llm/` | LLM Provider 封装 + 输出清洗 |
| `configs/` | Pydantic BaseSettings 配置管理 |
| `evaluation/` | 评估指标、blind judge、成本追踪、comparator 协议 |
| `memory/` | 辅助持久化模块，当前未接入默认 CLI 主工作流 |
| `skills/` | 主题模板包装器，当前未形成独立技能系统，也未接入默认 CLI 主工作流 |
| `mcp_servers/` | MCP 集成占位目录，当前未接入公开支持能力 |
| `scripts/` | benchmark runner、full comparison、报告导入与离线对比脚本 |

## 辅助与预留目录

以下目录当前存在于仓库中，但不属于默认 CLI 主工作流的公开能力面：

- `memory/`：辅助持久化模块，保留独立实现与测试，但当前未接入默认 CLI 主工作流。
- `skills/`：主题模板包装器，便于复用 `run_research()`，当前未形成独立技能系统，也未接入默认 CLI 主工作流。
- `mcp_servers/`：MCP 集成占位目录，当前未接入公开支持能力。
