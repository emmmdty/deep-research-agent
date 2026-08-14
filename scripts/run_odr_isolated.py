"""Open Deep Research (langchain-ai) isolated runner.

Executes the reference open-source deep research agent in a dedicated Python
environment (``open_deep_research`` requires langchain >= 0.3 while this repo
pins langchain 0.2, so it must not share the project venv), using the same
LLM endpoint and Tavily key as the rest of the repo, and writes the report
plus metadata for the head-to-head comparator suite.

Install in a separate environment:

    uv venv /tmp/odr-venv --clear
    uv pip install --python /tmp/odr-venv/bin/python open_deep_research

Usage:

    /tmp/odr-venv/bin/python scripts/run_odr_isolated.py \
        --topic "..." --report-path out.md --meta-path meta.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _configure_environment() -> None:
    """Point langchain-openai at the repo's configured endpoint."""
    if not os.environ.get("OPENAI_API_KEY") and os.environ.get("LLM_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["LLM_API_KEY"]
    if not os.environ.get("OPENAI_BASE_URL") and os.environ.get("LLM_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = os.environ["LLM_BASE_URL"]
    if not os.environ.get("OPENAI_MODEL_NAME") and os.environ.get("LLM_MODEL_NAME"):
        os.environ["OPENAI_MODEL_NAME"] = os.environ["LLM_MODEL_NAME"]
    os.environ.setdefault("TAVILY_API_KEY", os.environ.get("TAVILY_API_KEY", ""))


async def run_research(topic: str) -> str:
    """Run the reference Open Deep Research graph and return the final report."""
    from langchain_core.messages import HumanMessage

    # The OpenAI-compatible endpoint used by this repo does not support the
    # json_schema response_format that langchain's default structured output
    # sends; function calling is supported. The upstream model also rejects
    # tool_choice while thinking mode is on, so thinking is disabled via the
    # same extra_body this repo's own client uses.
    import langchain_openai

    _orig_with_structured_output = langchain_openai.ChatOpenAI.with_structured_output

    def _with_structured_output(self, schema, **kwargs):
        kwargs.setdefault("method", "function_calling")
        return _orig_with_structured_output(self, schema, **kwargs)

    langchain_openai.ChatOpenAI.with_structured_output = _with_structured_output

    from openai.resources.chat.completions import AsyncCompletions, Completions

    _orig_create = Completions.create
    _orig_async_create = AsyncCompletions.create

    def _with_thinking_off(kwargs):
        extra_body = dict(kwargs.get("extra_body") or {})
        extra_body.setdefault("thinking", {"type": "disabled"})
        kwargs["extra_body"] = extra_body
        return kwargs

    def _create_with_thinking_off(self, **kwargs):
        return _orig_create(self, **_with_thinking_off(kwargs))

    async def _async_create_with_thinking_off(self, **kwargs):
        return await _orig_async_create(self, **_with_thinking_off(kwargs))

    Completions.create = _create_with_thinking_off
    AsyncCompletions.create = _async_create_with_thinking_off

    from open_deep_research.deep_researcher import deep_researcher

    model_name = os.environ.get("OPENAI_MODEL_NAME", "deepseek-v4-flash")
    configurable_model = "openai:" + model_name
    result = await deep_researcher.ainvoke(
        {"messages": [HumanMessage(content=topic)]},
        config={
            "configurable": {
                "model": configurable_model,
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "max_tokens": 4096,
                "research_model": configurable_model,
                "summarization_model": configurable_model,
                "compression_model": configurable_model,
                "final_report_model": configurable_model,
            }
        },
    )
    report = str(result.get("final_report") or "")
    if not report.strip():
        raise RuntimeError("open_deep_research returned an empty report")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Open Deep Research in isolation")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--report-path", required=True, type=Path)
    parser.add_argument("--meta-path", required=True, type=Path)
    args = parser.parse_args()

    _configure_environment()
    started = time.monotonic()
    report = asyncio.run(run_research(args.topic))
    elapsed = round(time.monotonic() - started, 2)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    meta = {
        "comparator": "odr",
        "topic": args.topic,
        "model": os.environ.get("OPENAI_MODEL_NAME", "deepseek-v4-flash"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": elapsed,
        "report_chars": len(report),
    }
    args.meta_path.parent.mkdir(parents=True, exist_ok=True)
    args.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"odr: report written to {args.report_path} ({elapsed}s)")


if __name__ == "__main__":
    main()
