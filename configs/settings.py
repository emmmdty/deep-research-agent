"""项目配置管理，基于 Pydantic BaseSettings 自动加载 .env 文件。"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class SearchBackend(str, Enum):
    """支持的搜索后端类型。"""

    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"


class LLMProvider(str, Enum):
    """支持的 LLM 提供商。"""

    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    AGICTO = "agicto"
    CUSTOM = "custom"


# 项目根目录（deep-research-agent/）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """运行时配置，自动从 .env 文件读取环境变量。"""

    # ---------- LLM 配置 ----------
    llm_provider: LLMProvider = Field(
        default=LLMProvider.MINIMAX,
        description="LLM 提供商",
    )
    llm_model_name: str = Field(
        default="MiniMax-M2.5",
        description="模型名称",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="LLM API 密钥",
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="LLM API 基地址",
    )
    llm_temperature: float = Field(
        default=0.0,
        description="LLM 采样温度",
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="LLM 最大输出 token 数",
    )

    # ---------- 搜索配置 ----------
    search_backend: SearchBackend = Field(
        default=SearchBackend.TAVILY,
        description="默认搜索后端",
    )
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API 密钥",
    )

    # ---------- 研究流程配置 ----------
    max_research_loops: int = Field(
        default=3,
        description="最大迭代研究循环次数",
    )
    max_search_results: int = Field(
        default=5,
        description="每次搜索返回的最大结果数",
    )
    research_profile: str = Field(
        default="default",
        description="研究 profile：default 或 benchmark",
    )
    research_concurrency: int = Field(
        default=3,
        description="研究并发度",
    )
    critic_hard_fail_enabled: bool = Field(
        default=True,
        description="是否启用质量门控硬规则",
    )
    per_source_max_results: int = Field(
        default=4,
        description="单个来源的最多候选结果数",
    )
    per_task_selected_sources: int = Field(
        default=6,
        description="单个任务最多保留的来源数",
    )
    source_policy_mode: str = Field(
        default="default",
        description="来源选择策略模式",
    )
    enabled_capability_types: list[str] = Field(
        default_factory=lambda: ["builtin", "skill", "mcp"],
        description="启用的能力类型",
    )
    skill_paths: list[str] = Field(
        default_factory=list,
        description="skill 根目录列表",
    )
    mcp_config_path: Optional[str] = Field(
        default=None,
        description="MCP server YAML 配置路径",
    )
    mcp_servers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="MCP server 配置列表",
    )
    enabled_sources: list[str] = Field(
        default_factory=lambda: ["web", "github", "arxiv"],
        description="启用的研究来源",
    )
    enabled_comparators: list[str] = Field(
        default_factory=lambda: ["ours", "gptr", "odr", "alibaba"],
        description="启用的对比器",
    )
    judge_model: Optional[str] = Field(
        default=None,
        description="LLM Judge 模型名（默认跟随主模型）",
    )
    open_deep_research_command: Optional[str] = Field(
        default=None,
        description="Open Deep Research 运行命令模板",
    )
    open_deep_research_report_dir: Optional[str] = Field(
        default=None,
        description="Open Deep Research 报告导入目录",
    )
    alibaba_runner_mode: str = Field(
        default="command",
        description="Alibaba 对比器运行模式",
    )
    alibaba_command: Optional[str] = Field(
        default=None,
        description="Alibaba DeepResearch 运行命令模板",
    )
    alibaba_report_dir: Optional[str] = Field(
        default=None,
        description="Alibaba 报告导入目录",
    )
    gemini_enabled: bool = Field(
        default=False,
        description="是否启用 Gemini Deep Research 对比器",
    )
    gemini_allowlist_required: bool = Field(
        default=True,
        description="Gemini Deep Research 是否要求 allowlist",
    )
    gemini_command: Optional[str] = Field(
        default=None,
        description="Gemini Deep Research 运行命令模板",
    )
    gemini_report_dir: Optional[str] = Field(
        default=None,
        description="Gemini 报告导入目录",
    )
    gpt_researcher_python: Optional[str] = Field(
        default=None,
        description="GPT Researcher 隔离 Python 路径",
    )

    # ---------- Memory 配置 ----------
    workspace_dir: str = Field(
        default="workspace",
        description="研究工作区目录",
    )
    memory_backend: str = Field(
        default="sqlite",
        description="记忆后端，当前固定为 sqlite",
    )

    log_level: str = Field(default="INFO", description="日志级别")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator(
        "enabled_sources",
        "enabled_comparators",
        "enabled_capability_types",
        "skill_paths",
        mode="before",
    )
    @classmethod
    def _parse_csv_list(cls, value: Any) -> Any:
        """允许使用逗号分隔字符串配置列表字段。"""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("mcp_servers", mode="before")
    @classmethod
    def _parse_mcp_servers(cls, value: Any) -> Any:
        """允许使用 JSON 字符串配置 MCP server 列表。"""
        if isinstance(value, str) and value.strip():
            return json.loads(value)
        return value

    def get_llm_config(self) -> dict:
        """返回用于初始化 LLM 客户端的配置字典。"""

        # 根据 provider 自动匹配 API key 和 base_url
        provider_defaults = {
            LLMProvider.MINIMAX: {
                "env_key": "MINIMAX_API_KEY",
                "base_url": "https://api.minimaxi.com/v1",
                "model": "MiniMax-M2.5",
            },
            LLMProvider.DEEPSEEK: {
                "env_key": "DEEPSEEK_API_KEY",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
            },
            LLMProvider.AGICTO: {
                "env_key": "AGICTO_API_KEY",
                "base_url": "https://api.agicto.cn/v1",
                "model": "gpt-4o-mini",
            },
            LLMProvider.OPENAI: {
                "env_key": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
            },
        }

        defaults = provider_defaults.get(self.llm_provider, {})

        # 优先使用显式设置的值，否则使用 provider 默认值
        import os

        api_key = self.llm_api_key or os.getenv(defaults.get("env_key", ""), "")
        base_url = self.llm_base_url or defaults.get("base_url", "")
        model = self.llm_model_name or defaults.get("model", "")

        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
        }


# 全局单例
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局配置单例。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """清空全局配置缓存。"""
    global _settings
    _settings = None
