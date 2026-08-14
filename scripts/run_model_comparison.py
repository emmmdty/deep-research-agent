"""Multi-model comparison for the canonical scheduler-v2 agent.

Runs the same live research topics through the canonical scheduler-v2 pipeline
under three different models (same endpoint family, different price/quality
points), then judges every report blind with a fixed judge model. Produces an
honest cost/quality/latency table with committed per-run artifacts.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production \\
        uv run python scripts/run_model_comparison.py

Environment overrides: ``MODELS`` (comma list, default flash/v4/mini),
``MAX_TOPICS`` (default 3), ``JUDGE_MODEL`` (default deepseek-v4-flash).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from deep_research_agent.agents.llm import LLMChat  # noqa: E402
from legacy.evaluation.comparators import load_topics  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "evals" / "reports" / "live_benchmarks" / "model_comparison"

JUDGE_SYSTEM = (
    "You are a strict, fair judge for a research-quality comparison. Score the "
    "research report on a 1-10 scale per dimension. Consider factual accuracy, "
    "depth of analysis, citation quality, and structure. Respond with JSON only: "
    '{"depth": n, "accuracy": n, "citations": n, "overall": n, "comments": "..."}'
)


async def _judge(report: str, topic: str, judge_model: str) -> dict:
    try:
        chat = LLMChat()
        payload = await chat.chat_json(
            system=JUDGE_SYSTEM,
            user=f"Topic: {topic}\n\nReport:\n{report[:20000]}",
            max_tokens=256,
            temperature=0.0,
        )
        result = {
            "depth": float(payload.get("depth") or 0),
            "accuracy": float(payload.get("accuracy") or 0),
            "citations": float(payload.get("citations") or 0),
            "overall": float(payload.get("overall") or 0),
            "comments": str(payload.get("comments") or ""),
            "judge_model": judge_model,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("judge failed for {}: {}", topic, exc)
        result = {"depth": 0.0, "accuracy": 0.0, "citations": 0.0, "overall": 0.0, "comments": f"judge error: {exc}", "judge_model": judge_model}
    return result


def _run_one(model: str, topic, out_dir: Path) -> dict:
    """Run the canonical agent under ``model`` for one topic (subprocess)."""
    report_path = out_dir / model / f"{topic.id}.md"
    meta_path = out_dir / model / f"{topic.id}_meta.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists() and meta_path.exists():
        return {
            "model": model,
            "topic_id": topic.id,
            "topic": topic.topic,
            "report_path": str(report_path),
            "meta": json.loads(meta_path.read_text(encoding="utf-8")),
            "report": report_path.read_text(encoding="utf-8"),
        }
    env = os.environ.copy()
    env["LLM_MODEL_NAME"] = model
    env["SCHEDULER_RUNTIME_MODE"] = "production"
    command = [
        str(sys.executable),
        str(PROJECT_ROOT / "scripts" / "run_ours_v2_isolated.py"),
        "--topic",
        topic.topic,
        "--report-path",
        str(report_path),
        "--meta-path",
        str(meta_path),
    ]
    logger.info("[{}|{}] running agent...", model, topic.id)
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        check=False,
    )
    if completed.returncode != 0 or not report_path.exists():
        logger.error("[{}|{}] failed: {}", model, topic.id, completed.stderr[-500:])
        return {
            "model": model,
            "topic_id": topic.id,
            "topic": topic.topic,
            "status": "failed",
            "error": completed.stderr[-800:],
            "wall_seconds": round(time.monotonic() - started, 2),
        }
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["wall_seconds"] = round(time.monotonic() - started, 2)
    return {
        "model": model,
        "topic_id": topic.id,
        "topic": topic.topic,
        "report_path": str(report_path),
        "meta": meta,
        "report": report_path.read_text(encoding="utf-8"),
    }


def _write_summary(runs: list[dict], out_dir: Path, judge_model: str) -> dict:
    by_model = {}
    for run in runs:
        by_model.setdefault(run["model"], []).append(run)
    rows = []
    for model in sorted(by_model):
        model_runs = by_model[model]
        finished = [r for r in model_runs if r.get("report")]
        total_cost = sum(r["meta"].get("cost", {}).get("estimated_cost_usd", 0.0) for r in finished)
        total_tokens = sum(r["meta"].get("cost", {}).get("total_tokens", 0) for r in finished)
        total_wall = sum(r.get("meta", {}).get("wall_seconds", 0.0) or r.get("wall_seconds", 0.0) for r in model_runs)
        rows.append(
            {
                "model": model,
                "topics_completed": len(finished),
                "topics_total": len(model_runs),
                "avg_judge_overall": round(
                    sum(r["judge"]["overall"] for r in finished) / len(finished), 2
                )
                if finished
                else 0.0,
                "avg_judge_accuracy": round(
                    sum(r["judge"]["accuracy"] for r in finished) / len(finished), 2
                )
                if finished
                else 0.0,
                "avg_claims": round(sum(r["meta"].get("claims", 0) for r in finished) / len(finished), 1)
                if finished
                else 0,
                "avg_sources": round(sum(r["meta"].get("sources", 0) for r in finished) / len(finished), 1)
                if finished
                else 0,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "total_wall_seconds": round(total_wall, 2),
            }
        )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "judge_model": judge_model,
        "per_model": rows,
        "per_run": [
            {
                "model": r["model"],
                "topic_id": r["topic_id"],
                "status": r.get("status", "completed"),
                "judge": r.get("judge"),
                "claims": r.get("meta", {}).get("claims"),
                "sources": r.get("meta", {}).get("sources"),
                "tokens": r.get("meta", {}).get("cost", {}).get("total_tokens"),
                "cost_usd": r.get("meta", {}).get("cost", {}).get("estimated_cost_usd"),
                "wall_seconds": r.get("meta", {}).get("wall_seconds"),
            }
            for r in runs
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Multi-Model Comparison — Canonical Scheduler-V2 Agent",
        "",
        "The same live research topics run through the canonical scheduler-v2 pipeline "
        "under different models (same OpenAI-compatible endpoint family). Every report "
        "is judged blind by a fixed judge model.",
        "",
        f"- Judge model: `{judge_model}`",
        "",
        "| Model | Topics | Judge Ø | Accuracy Ø | Claims Ø | Sources Ø | Tokens | Cost USD | Wall (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['topics_completed']}/{row['topics_total']} | "
            f"{row['avg_judge_overall']} | {row['avg_judge_accuracy']} | {row['avg_claims']} | "
            f"{row['avg_sources']} | {row['total_tokens']} | {row['total_cost_usd']} | {row['total_wall_seconds']} |"
        )
    lines.extend(["", "## Per-Run Details", ""])
    for r in runs:
        status = r.get("status", "completed")
        judge = r.get("judge") or {}
        lines.append(
            f"### {r['model']} / {r['topic_id']} — {status}\n"
            f"- Judge: overall {judge.get('overall', '-')}, accuracy {judge.get('accuracy', '-')}, "
            f"citations {judge.get('citations', '-')}\n"
            f"- Claims: {r.get('meta', {}).get('claims', '-')} | Sources: {r.get('meta', {}).get('sources', '-')} | "
            f"Tokens: {r.get('meta', {}).get('cost', {}).get('total_tokens', '-')} | "
            f"Cost: ${r.get('meta', {}).get('cost', {}).get('estimated_cost_usd', '-')} | "
            f"Wall: {r.get('meta', {}).get('wall_seconds', '-')}s\n"
            f"- Judge comments: {judge.get('comments', '-')}"
        )
        if r.get("error"):
            lines.append(f"- Error: {r['error']}")
        lines.append("")
    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-model comparison")
    parser.add_argument("--models", default=os.environ.get("MODELS", "deepseek-v4-flash,deepseek-v4,gpt-4o-mini"))
    parser.add_argument("--max-topics", type=int, default=3)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "deepseek-v4-flash"))
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    topics = load_topics(max_topics=args.max_topics)
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for model in models:
        for topic in topics:
            run = _run_one(model, topic, args.out_dir)
            if run.get("report"):
                run["judge"] = asyncio.run(_judge(run["report"], topic.topic, args.judge_model))
            runs.append(run)
    summary = _write_summary(runs, args.out_dir, args.judge_model)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
