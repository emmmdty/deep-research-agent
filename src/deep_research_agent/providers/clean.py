"""LLM 输出清洗工具——移除模型思维链泄露等无关内容。"""

from __future__ import annotations

import re


def clean_llm_output(text: str) -> str:
    """清理 LLM 输出中的杂质内容。

    处理内容包括：
        - <think>...</think> 思维链标签（MiniMax / DeepSeek R1 等模型）
        - ```json ... ``` 代码块外壳（保留内部 JSON）
    """
    if not text:
        return text

    # 移除 <think>...</think> 思维链标签（含多行内容）
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # 清理首尾空行
    text = text.strip()

    return text


def extract_json_from_output(text: str) -> str:
    """从 LLM 输出中提取 JSON 字符串。

    优先提取 JSON 代码块内的内容，否则直接返回清理后的文本。
    """
    text = clean_llm_output(text)

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text
