"""Project settings and Phase 2 provider/profile foundations."""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from deep_research_agent.common import DEFAULT_SOURCE_PROFILE, resolve_source_profile_name
from deep_research_agent.providers.models import ProviderCapabilities, ProviderProfile, ProviderType


class SearchBackend(str, Enum):
    """支持的搜索后端类型。"""

    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"


class LLMProvider(str, Enum):
    """Canonical provider classes exposed by the runtime."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


# 项目根目录（deep-research-agent/）
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """运行时配置，自动从 .env 文件读取环境变量。"""

    # ---------- LLM 配置 ----------
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI_COMPATIBLE,
        description="默认 provider profile",
    )
    llm_model_name: str = Field(
        default="MiniMax-M2.5",
        description="当前默认 provider profile 的模型名称覆盖",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="当前默认 provider profile 的 API key 覆盖",
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="当前默认 provider profile 的 base URL 覆盖",
    )
    llm_temperature: float = Field(
        default=0.0,
        description="LLM 采样温度",
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="LLM 最大输出 token 数",
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API 密钥")
    openai_model_name: str = Field(default="gpt-4o-mini", description="OpenAI 默认模型")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API 密钥")
    anthropic_model_name: str = Field(
        default="claude-3-5-haiku-latest",
        description="Anthropic 默认模型",
    )
    openai_compatible_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI-compatible API 密钥",
    )
    openai_compatible_base_url: Optional[str] = Field(
        default=None,
        description="OpenAI-compatible base URL",
    )
    openai_compatible_model_name: str = Field(
        default="MiniMax-M2.5",
        description="OpenAI-compatible 默认模型",
    )
    anthropic_compatible_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic-compatible API 密钥",
    )
    anthropic_compatible_base_url: Optional[str] = Field(
        default=None,
        description="Anthropic-compatible base URL",
    )
    anthropic_compatible_model_name: str = Field(
        default="claude-compatible-model",
        description="Anthropic-compatible 默认模型",
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
        description="研究 profile 名称",
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
    case_study_official_domains: list[str] = Field(
        default_factory=lambda: [
            "openai.com",
            "anthropic.com",
            "langchain.com",
            "microsoft.com",
            "learn.microsoft.com",
            "aws.amazon.com",
            "cloud.google.com",
            "salesforce.com",
            "ibm.com",
            "huggingface.co",
        ],
        description="case-study 检索时优先尝试的官方域名",
    )
    source_policy_mode: str = Field(
        default=DEFAULT_SOURCE_PROFILE,
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
    # ---------- Memory 配置 ----------
    workspace_dir: str = Field(
        default="workspace",
        description="研究工作区目录",
    )
    bundle_emission_enabled: bool = Field(
        default=True,
        description="是否输出 report bundle sidecar",
    )
    bundle_output_dirname: str = Field(
        default="bundles",
        description="sidecar bundle 输出目录名",
    )
    job_runtime_dirname: str = Field(
        default="research_jobs",
        description="job runtime 目录名",
    )
    job_heartbeat_interval_seconds: int = Field(
        default=2,
        description="worker 心跳间隔（秒）",
    )
    job_stale_timeout_seconds: int = Field(
        default=15,
        description="stale job 判定阈值（秒）",
    )
    connector_substrate_enabled: bool = Field(
        default=True,
        description="是否启用 connector substrate",
    )
    snapshot_store_dirname: str = Field(
        default="snapshots",
        description="snapshot store 目录名",
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
        "enabled_capability_types",
        "skill_paths",
        "case_study_official_domains",
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

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_provider_alias(cls, value: Any) -> Any:
        if isinstance(value, str):
            aliases = {
                "minimax": LLMProvider.OPENAI_COMPATIBLE.value,
                "deepseek": LLMProvider.OPENAI_COMPATIBLE.value,
                "agicto": LLMProvider.OPENAI_COMPATIBLE.value,
                "custom": LLMProvider.OPENAI_COMPATIBLE.value,
            }
            return aliases.get(value, value)
        return value

    @field_validator("source_policy_mode", mode="before")
    @classmethod
    def _normalize_source_policy_mode(cls, value: Any) -> Any:
        if value is None:
            return DEFAULT_SOURCE_PROFILE
        if isinstance(value, str):
            return resolve_source_profile_name(value)
        return value

    def get_default_provider_profile_name(self) -> str:
        return self.llm_provider.value

    def get_provider_profiles(self) -> dict[str, ProviderProfile]:
        """Build canonical provider profiles with legacy env fallbacks."""

        selected_profile = self.get_default_provider_profile_name()

        def _pick(explicit: str | None, generic: str | None, fallback: str | None, *, profile_name: str) -> str | None:
            if explicit:
                return explicit
            if profile_name == selected_profile and generic:
                return generic
            return fallback

        selected_generic_model = self.llm_model_name if selected_profile else None

        profiles = {
            "openai": ProviderProfile(
                name="openai",
                provider_type=ProviderType.OPENAI,
                model=_pick(None, selected_generic_model, self.openai_model_name, profile_name="openai")
                or self.openai_model_name,
                api_key=_pick(
                    self.openai_api_key,
                    self.llm_api_key,
                    os.getenv("OPENAI_API_KEY"),
                    profile_name="openai",
                ),
                base_url=_pick(None, self.llm_base_url, "https://api.openai.com/v1", profile_name="openai"),
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens,
                priority=10,
                capabilities=ProviderCapabilities(
                    reasoning=True,
                    structured_output=True,
                    fast=True,
                    file_understanding=True,
                ),
            ),
            "anthropic": ProviderProfile(
                name="anthropic",
                provider_type=ProviderType.ANTHROPIC,
                model=_pick(
                    None,
                    selected_generic_model,
                    self.anthropic_model_name,
                    profile_name="anthropic",
                )
                or self.anthropic_model_name,
                api_key=_pick(
                    self.anthropic_api_key,
                    self.llm_api_key,
                    os.getenv("ANTHROPIC_API_KEY"),
                    profile_name="anthropic",
                ),
                base_url=_pick(None, self.llm_base_url, "https://api.anthropic.com", profile_name="anthropic"),
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens,
                priority=10,
                capabilities=ProviderCapabilities(
                    reasoning=True,
                    structured_output=True,
                    judge_preferred=True,
                ),
            ),
            "openai_compatible": ProviderProfile(
                name="openai_compatible",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
                model=(
                    self.llm_model_name
                    if selected_profile == "openai_compatible" and self.llm_model_name
                    else self.openai_compatible_model_name
                ),
                api_key=_pick(
                    self.openai_compatible_api_key,
                    self.llm_api_key,
                    os.getenv("OPENAI_COMPATIBLE_API_KEY")
                    or os.getenv("MINIMAX_API_KEY")
                    or os.getenv("DEEPSEEK_API_KEY")
                    or os.getenv("AGICTO_API_KEY"),
                    profile_name="openai_compatible",
                ),
                base_url=_pick(
                    self.openai_compatible_base_url,
                    self.llm_base_url,
                    os.getenv("OPENAI_COMPATIBLE_BASE_URL") or "https://api.minimaxi.com/v1",
                    profile_name="openai_compatible",
                ),
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens,
                priority=25,
                capabilities=ProviderCapabilities(
                    reasoning=True,
                    structured_output=True,
                    fast=True,
                ),
                metadata={"legacy_aliases": ["minimax", "deepseek", "agicto", "custom"]},
            ),
            "anthropic_compatible": ProviderProfile(
                name="anthropic_compatible",
                provider_type=ProviderType.ANTHROPIC_COMPATIBLE,
                model=(
                    self.llm_model_name
                    if selected_profile == "anthropic_compatible" and self.llm_model_name
                    else self.anthropic_compatible_model_name
                ),
                api_key=_pick(
                    self.anthropic_compatible_api_key,
                    self.llm_api_key,
                    os.getenv("ANTHROPIC_COMPATIBLE_API_KEY"),
                    profile_name="anthropic_compatible",
                ),
                base_url=_pick(
                    self.anthropic_compatible_base_url,
                    self.llm_base_url,
                    os.getenv("ANTHROPIC_COMPATIBLE_BASE_URL"),
                    profile_name="anthropic_compatible",
                ),
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens,
                priority=30,
                capabilities=ProviderCapabilities(
                    reasoning=True,
                    structured_output=True,
                    judge_preferred=True,
                ),
            ),
        }
        return profiles

    def get_llm_config(self) -> dict:
        """Return the resolved config for the selected provider profile."""

        profile = self.get_provider_profiles()[self.get_default_provider_profile_name()]
        return {
            "api_key": profile.api_key or "",
            "base_url": profile.base_url or "",
            "model": profile.model,
            "temperature": profile.temperature,
            "max_tokens": profile.max_tokens,
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
