"""安全沙箱代码执行工具——在子进程中执行 Python 代码片段。"""

from __future__ import annotations

import subprocess
import tempfile

from langchain_core.tools import tool
from loguru import logger


@tool
def code_executor_tool(code: str, timeout: int = 30) -> str:
    """在隔离的子进程中执行 Python 代码片段。

    Args:
        code: 要执行的 Python 代码字符串。
        timeout: 执行超时时间（秒），默认 30。

    Returns:
        代码的标准输出和标准错误。
    """
    try:
        # 将代码写入临时文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_path = f.name

        # 在子进程中执行
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )

        output = ""
        if result.stdout:
            output += f"标准输出:\n{result.stdout}\n"
        if result.stderr:
            output += f"标准错误:\n{result.stderr}\n"
        if result.returncode != 0:
            output += f"退出码: {result.returncode}\n"

        if not output.strip():
            output = "代码执行完成，无输出。"

        logger.info("代码执行完成: 退出码={}", result.returncode)
        return output[:5000]

    except subprocess.TimeoutExpired:
        logger.warning("代码执行超时: timeout={}s", timeout)
        return f"代码执行超时（{timeout}秒）。"
    except Exception as e:
        logger.error("代码执行失败: {}", e)
        return f"代码执行失败: {e}"
