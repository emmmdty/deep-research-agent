# AGENTS.md

本项目使用 AI Agent 辅助开发。以下规范以仓库当前实现为准，优先反映已经落地的代码与脚本，而不是计划中的能力。

## 项目现状

- Deep Research Agent 是一个基于 LangGraph 的多智能体深度研究系统，当前以 **CLI-first** 方式运行。
- 主工作流为：`Supervisor -> Planner -> Researcher -> Critic -> Writer`，其中 Critic 可驱动多轮补充研究。
- Researcher 已从单一搜索结果拼接升级为 **多源证据采集**，当前默认来源包含 `web`、`github`、`arxiv`。
- 项目同时提供统一 benchmark / comparator harness：
  - `scripts/run_benchmark.py`
  - `scripts/full_comparison.py`
  - `evaluation/comparators.py`
- 当前没有受支持的 HTTP API；若未来重新引入服务端接口，必须先补真实实现，再开放文档与依赖。
- `memory/`、`skills/` 当前为辅助目录，不属于默认 CLI 主工作流的公开能力面。
- `mcp_servers/` 当前为可选占位目录，不属于已公开支持能力。

## 代码风格

- Python 3.10+
- 必须使用类型注解（type hints）
- 注释、文档字符串、用户可见说明优先使用中文
- 结构化状态与数据对象优先使用 Pydantic v2
- 日志统一使用 Loguru
- 依赖与命令统一走 `uv`

## 架构约束

- 保持模块边界清晰：`agents/`、`tools/`、`workflows/`、`evaluation/`、`memory/`、`configs/` 分责明确。
- LangGraph 工作流由 `workflows/graph.py` 驱动；新增节点或状态时，同步更新状态定义与条件路由。
- 研究状态以 `workflows/states.py` 中的结构化对象为准，重点包括：
  - `SourceRecord`
  - `EvidenceNote`
  - `RunMetrics`
  - `ReportArtifact`
- 迭代研究相关的列表状态当前采用**覆盖式合并**而不是追加式合并，避免多轮循环时重复累计旧来源与旧总结。
- LLM 调用统一经过 `llm/provider.py`，不要绕开 provider 直接散落实例化模型。
- 搜索与评测相关改动需要同步考虑：
  - `tools/`
  - `evaluation/metrics.py`
  - `evaluation/llm_judge.py`
  - `evaluation/comparators.py`

## Benchmark 与 Comparator 约束

- comparator 的统一输出协议以 `evaluation/comparators.py` 中的 `ComparatorResult` 为准。
- 当前主 comparator 集合：
  - `ours`
  - `gptr`
  - `odr`
  - `alibaba`
- `gptr` 依赖隔离 Python 环境；`odr`、`alibaba` 优先走命令模板或报告导入目录。
- `gemini` 为可选 comparator，允许返回 `skipped`，但不能伪装成已接通。
- 外部 comparator 接入优先使用：
  - `.env` / `configs/settings.py` 中的命令模板
  - 报告导入目录
- 禁止在 runner 或脚本中硬编码 API Key、固定私有 base URL、Windows 专用绝对路径。
- `scripts/run_gptr_isolated.py` 只能从环境变量构造运行环境，不能回填硬编码凭证。
- `scripts/compare_agents.py` 目前定位为**单次离线文件/双报告比较工具**，不是主 benchmark 入口。

## 测试与验证

- 测试收集范围以 `pytest.ini` 为准，只收集 `tests/`。
- 新功能、行为变更、benchmark/comparator 改动必须补充或更新回归测试。
- 常用验证命令：
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run python main.py --help`
  - `uv run python scripts/run_benchmark.py --help`
  - `uv run python scripts/full_comparison.py --help`
- 不要声称某个 comparator “已支持 / 已跑通”，除非：
  - 命令模板或导入目录已经配置
  - 对应测试或实际命令已验证

## 文档同步要求

- 涉及架构、入口命令、benchmark 或 comparator 行为变化时，至少同步检查：
  - `README.md`
  - `README.zh-CN.md`
  - `docs/architecture.md`
  - `docs/development.md`
- 文档必须与当前代码一致；不要保留“未来可能支持”的旧说法，尤其是：
  - 不要把不存在的 API 写成可用接口
  - 不要把可选 comparator 写成默认可运行

## 提交规范

- 使用 Conventional Commits 格式
- 提交信息使用中文
- 示例：
  - `feat: 添加统一 comparator registry`
  - `fix: 修正研究状态重复累积问题`
  - `docs: 同步 benchmark 与 CLI 文档`
