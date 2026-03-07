# AGENTS.md

本项目使用 AI Agent 辅助开发。以下是开发规范：

## 项目概述

Deep Research Agent 是一个基于 LangGraph 的多智能体深度研究系统。

## 代码风格

- Python 3.10+
- 类型注解（type hints）
- 中文注释和文档字符串
- Pydantic v2 数据模型
- Loguru 日志

## 架构原则

- 模块化设计：agents / tools / workflows / memory 独立模块
- LangGraph 状态图驱动工作流
- 统一 LLM Provider 封装
- 工具系统可插拔

## 提交规范

- 使用 Conventional Commits 格式
- 中文提交信息
- 示例：`feat: 添加 arXiv 搜索工具`
