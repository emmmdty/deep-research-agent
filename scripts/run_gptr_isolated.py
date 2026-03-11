"""GPT Researcher 隔离运行脚本。

在独立 Python 环境中执行 GPT Researcher，并把报告与元数据落盘。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def build_runner_environment(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """构建 GPT Researcher 运行环境，不注入硬编码密钥。"""
    env = os.environ.copy()
    if base_env:
        env.update(base_env)

    env["PYTHONIOENCODING"] = "utf-8"

    # 允许复用当前项目的 LLM/OpenAI 风格配置。
    if not env.get("OPENAI_API_KEY") and env.get("LLM_API_KEY"):
        env["OPENAI_API_KEY"] = env["LLM_API_KEY"]
    if not env.get("OPENAI_BASE_URL") and env.get("LLM_BASE_URL"):
        env["OPENAI_BASE_URL"] = env["LLM_BASE_URL"]

    env.setdefault("FAST_LLM", env.get("GPT_RESEARCHER_FAST_LLM", "openai:gpt-4o-mini"))
    env.setdefault("SMART_LLM", env.get("GPT_RESEARCHER_SMART_LLM", env["FAST_LLM"]))
    env.setdefault("STRATEGIC_LLM", env.get("GPT_RESEARCHER_STRATEGIC_LLM", env["SMART_LLM"]))
    if env.get("OPENAI_API_KEY"):
        env.setdefault("EMBEDDING", env.get("GPT_RESEARCHER_EMBEDDING", "custom:text-embedding-3-small"))

    return env


def _configure_stdio() -> None:
    """强制 stdout/stderr 使用 UTF-8。"""
    if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure") and sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


async def run_research(topic: str) -> str:
    """异步运行 GPT Researcher 并返回报告。"""
    from gpt_researcher import GPTResearcher

    researcher = GPTResearcher(
        query=topic,
        report_type="research_report",
    )
    await researcher.conduct_research()
    return await researcher.write_report()


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="GPT Researcher 隔离运行器")
    parser.add_argument("--topic", required=True, help="研究主题")
    parser.add_argument("--output", required=True, help="报告输出路径")
    parser.add_argument("--meta", required=True, help="元数据输出路径（JSON）")
    args = parser.parse_args()

    os.environ.update(build_runner_environment())
    _configure_stdio()

    output_path = Path(args.output)
    meta_path = Path(args.meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    meta: dict[str, object]

    try:
        report = asyncio.run(run_research(args.topic))
        output_path.write_text(report, encoding="utf-8")
        meta = {
            "success": True,
            "status": "completed",
            "time_seconds": round(time.time() - start, 2),
            "word_count": len(report),
            "error": "",
        }
    except Exception:
        import traceback

        meta = {
            "success": False,
            "status": "failed",
            "time_seconds": round(time.time() - start, 2),
            "word_count": 0,
            "error": traceback.format_exc(),
        }

    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if meta["success"]:
        print(f"✅ GPT Researcher 完成: {meta['word_count']} 字, 耗时 {meta['time_seconds']}s")
    else:
        print(f"❌ GPT Researcher 失败: {meta['error']}")


if __name__ == "__main__":
    main()
