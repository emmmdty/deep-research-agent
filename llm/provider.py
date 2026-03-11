"""统一 LLM Provider 封装，支持 MiniMax / DeepSeek / OpenAI 等兼容 API。

通过 langchain-openai 的 ChatOpenAI 实现，因为上述 provider 均兼容 OpenAI 格式。
"""

from __future__ import annotations

from typing import Optional

from langchain_openai import ChatOpenAI
from loguru import logger

from configs.settings import Settings, get_settings
from evaluation.cost_tracker import get_tracker


def _estimate_tokens_from_text(text: str) -> int:
    """粗略估算 token 数。"""
    if not text:
        return 0
    return max(len(text) // 4, 1)


def _extract_token_usage(response) -> tuple[int, int]:
    """从响应对象中提取 token 使用量。"""
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = metadata.get("token_usage") or metadata.get("usage") or {}
    input_tokens = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("prompt_token_count")
        or 0
    )
    output_tokens = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("candidates_token_count")
        or 0
    )

    if input_tokens or output_tokens:
        return input_tokens, output_tokens

    content = getattr(response, "content", "")
    return 0, _estimate_tokens_from_text(str(content))


class TrackedChatOpenAI(ChatOpenAI):
    """带成本埋点的 ChatOpenAI。"""

    def invoke(self, input, config=None, **kwargs):
        response = super().invoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return response

    async def ainvoke(self, input, config=None, **kwargs):
        response = await super().ainvoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return response


class LLMProvider:
    """LLM 统一调用接口。
    
    封装 ChatOpenAI，利用 OpenAI 兼容格式统一调用 MiniMax / DeepSeek 等。
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._llm: TrackedChatOpenAI | None = None

    @property
    def llm(self) -> TrackedChatOpenAI:
        """懒加载 ChatOpenAI 实例。"""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> TrackedChatOpenAI:
        """根据配置创建 ChatOpenAI 实例。"""
        config = self._settings.get_llm_config()
        logger.info(
            "初始化 LLM: provider={}, model={}, base_url={}",
            self._settings.llm_provider.value,
            config["model"],
            config["base_url"],
        )

        return TrackedChatOpenAI(
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


def get_llm(settings: Optional[Settings] = None) -> TrackedChatOpenAI:
    """获取 ChatOpenAI 实例的便捷函数。"""
    provider = LLMProvider(settings)
    return provider.llm
