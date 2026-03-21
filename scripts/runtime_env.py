"""脚本运行时的环境变量加载辅助。"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from configs.settings import PROJECT_ROOT, reset_settings


def load_runtime_env(env_file: str | None = None) -> Path | None:
    """加载指定 env 文件并刷新 Settings 缓存。"""
    candidate = Path(env_file).expanduser() if env_file else (PROJECT_ROOT / ".env")
    if not candidate.exists():
        reset_settings()
        return None

    load_dotenv(candidate, override=True)
    _sanitize_proxy_env()
    reset_settings()
    return candidate


def _sanitize_proxy_env() -> None:
    """在未安装 socksio 时，移除会导致 httpx 失败的 SOCKS 代理。"""
    if importlib.util.find_spec("socksio") is not None:
        return

    for key in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(key, "")
        if value.lower().startswith("socks5://") or value.lower().startswith("socks://"):
            logger.warning("检测到 {} 使用 SOCKS 代理但未安装 socksio，已在当前进程移除该代理配置", key)
            os.environ.pop(key, None)
