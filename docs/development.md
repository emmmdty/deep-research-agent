# 开发指南

## 环境搭建

```bash
# 克隆仓库
git clone https://github.com/emmmdty/deep-research-agent.git
cd deep-research-agent

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API 密钥
```

## 开发流程

### 新增 Agent

1. 在 `agents/` 下创建新文件（如 `agents/my_agent.py`）
2. 定义 LangGraph node 函数：接收 `state: dict` 返回 `dict`
3. 在 `workflows/graph.py` 中注册节点和边
4. 如需要，在 `workflows/graph.py` 的 `GraphState` 中添加新的状态字段

### 新增工具

1. 在 `tools/` 下创建新文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `tools/__init__.py` 中导出

### 新增提示词

1. 在 `prompts/templates.py` 中添加 `SYSTEM_PROMPT` 和 `USER_PROMPT`
2. User prompt 使用 `{variable}` 格式的占位符

### 新增评估指标

1. 在 `evaluation/metrics.py` 中添加指标函数
2. 在 `evaluation/__init__.py` 中导出

## 常用命令

```bash
# 运行研究
uv run python main.py --topic "你的研究主题"

# 运行 Benchmark
uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba --max-topics 3

# 运行全量 comparator 对比
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba

# 离线文件对比
uv run python scripts/compare_agents.py --file-a our.md --file-b competitor.md
```

## 代码规范

- **Python**: 3.10+，使用类型注解
- **注释**: 中文
- **日志**: 使用 `loguru` 的 `logger.info/warning/error`
- **提交**: 中文 Conventional Commits（`feat:` / `fix:` / `docs:`）
