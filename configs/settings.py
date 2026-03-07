"""项目配置管理，基于 Pydantic BaseSettings 自动加载 .env 文件。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field
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

    # ---------- Memory 配置 ----------
    workspace_dir: str = Field(
        default="workspace",
        description="研究工作区目录",
    )

    # ---------- 服务配置 ----------
    host: str = Field(default="0.0.0.0", description="API 服务绑定地址")
    port: int = Field(default=8000, description="API 服务端口")
    log_level: str = Field(default="INFO", description="日志级别")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

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
