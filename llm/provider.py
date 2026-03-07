"""统一 LLM Provider 封装，支持 MiniMax / DeepSeek / OpenAI 等兼容 API。

通过 langchain-openai 的 ChatOpenAI 实现，因为上述 provider 均兼容 OpenAI 格式。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI
from loguru import logger

from configs.settings import Settings, get_settings


class LLMProvider:
    """LLM 统一调用接口。
    
    封装 ChatOpenAI，利用 OpenAI 兼容格式统一调用 MiniMax / DeepSeek 等。
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._llm: ChatOpenAI | None = None

    @property
    def llm(self) -> ChatOpenAI:
        """懒加载 ChatOpenAI 实例。"""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> ChatOpenAI:
        """根据配置创建 ChatOpenAI 实例。"""
        config = self._settings.get_llm_config()
        logger.info(
            "初始化 LLM: provider={}, model={}, base_url={}",
            self._settings.llm_provider.value,
            config["model"],
            config["base_url"],
        )

        return ChatOpenAI(
            model=config["model"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )

    def chat(self, messages: list[dict]) -> str:
        """同步调用 LLM，返回文本响应。
        
        Args:
            messages: OpenAI 格式的消息列表，例如
                [{"role": "user", "content": "你好"}]
        
        Returns:
            LLM 返回的文本内容。
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = self.llm.invoke(lc_messages)
        return response.content

    async def achat(self, messages: list[dict]) -> str:
        """异步调用 LLM，返回文本响应。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = await self.llm.ainvoke(lc_messages)
        return response.content


def get_llm(settings: Optional[Settings] = None) -> ChatOpenAI:
    """获取 ChatOpenAI 实例的便捷函数。"""
    provider = LLMProvider(settings)
    return provider.llm
