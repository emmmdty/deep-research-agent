"""LLM 命名空间。

避免在 import llm.clean 时提前触发 provider 侧的重型依赖和循环导入。
"""

__all__ = ["LLMProvider", "get_llm"]


def __getattr__(name: str):
    if name in {"LLMProvider", "get_llm"}:
        from llm.provider import LLMProvider, get_llm

        return {"LLMProvider": LLMProvider, "get_llm": get_llm}[name]
    raise AttributeError(name)
