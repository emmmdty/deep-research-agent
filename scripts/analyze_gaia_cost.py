"""Retrospective cost-accuracy analysis of the committed GAIA live lane.

Every per-question record in the GAIA live lane carries its own token/cost
telemetry; this script aggregates that committed data into the cost-accuracy
view an agent-infra interview asks for: how much do we spend per correct
answer, and does spending more tokens correlate with correctness?

No new provider calls — pure analysis of committed evidence.

Usage:
    uv run python scripts/analyze_gaia_cost.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAIA_DIR = ROOT / "evals" / "reports" / "live_benchmarks" / "gaia_real"
OUT_DIR = ROOT / "evals" / "reports" / "live_benchmarks" / "cost_analysis"


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def main() -> None:
    rows: list[dict] = []
    for record_dir in sorted(GAIA_DIR.glob("*")):
        record_path = record_dir / "record.json"
        if not record_path.exists():
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        cost = record.get("cost", {}) or {}
        correct = bool((record.get("grade") or {}).get("correct"))
        rows.append(
            {
                "task_id": record["task_id"],
                "level": record["level"],
                "correct": correct,
                "exact_match": bool(record.get("exact_match")),
                "tokens": int(cost.get("total_tokens") or 0),
                "llm_calls": int(cost.get("llm_calls") or 0),
                "search_calls": int(cost.get("search_calls") or 0),
                "cost_usd": float(cost.get("estimated_cost_usd") or 0.0),
                "wall_seconds": float(cost.get("wall_seconds") or 0.0),
            }
        )
    if not rows:
        raise SystemExit(f"no GAIA records found under {GAIA_DIR}")

    correct_rows = [row for row in rows if row["correct"]]
    incorrect_rows = [row for row in rows if not row["correct"]]
    total_tokens = sum(row["tokens"] for row in rows)
    total_cost = sum(row["cost_usd"] for row in rows)
    per_correct_cost = total_cost / len(correct_rows) if correct_rows else 0.0

    def _stats(selected: list[dict]) -> dict:
        return {
            "n": len(selected),
            "median_tokens": round(_median([row["tokens"] for row in selected])),
            "mean_tokens": round(sum(row["tokens"] for row in selected) / len(selected))
            if selected
            else 0,
            "median_llm_calls": _median([row["llm_calls"] for row in selected]),
            "median_search_calls": _median([row["search_calls"] for row in selected]),
            "median_wall_seconds": round(_median([row["wall_seconds"] for row in selected]), 1),
            "mean_cost_usd": round(sum(row["cost_usd"] for row in selected) / len(selected), 4)
            if selected
            else 0.0,
        }

    tokens_by_correctness = {
        "correct": _stats(correct_rows),
        "incorrect": _stats(incorrect_rows),
        "all": _stats(rows),
    }

    sorted_by_tokens = sorted(rows, key=lambda row: row["tokens"])
    top_half_tokens = sorted_by_tokens[len(sorted_by_tokens) // 2 :]
    bottom_half_tokens = sorted_by_tokens[: len(sorted_by_tokens) // 2]
    cost_correlation = {
        "higher_token_half_correct_rate": round(
            sum(1 for row in top_half_tokens if row["correct"]) / len(top_half_tokens), 4
        ),
        "lower_token_half_correct_rate": round(
            sum(1 for row in bottom_half_tokens if row["correct"]) / len(bottom_half_tokens), 4
        ),
        "tokens_correct_vs_incorrect_ratio": round(
            _stats(correct_rows)["mean_tokens"] / _stats(incorrect_rows)["mean_tokens"], 3
        )
        if incorrect_rows
        else None,
    }

    summary = {
        "questions": len(rows),
        "correct": len(correct_rows),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "cost_per_correct_answer_usd": round(per_correct_cost, 4),
        "tokens_by_correctness": tokens_by_correctness,
        "cost_correlation": cost_correlation,
        "per_question": sorted(rows, key=lambda row: row["tokens"]),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.joinpath("cost_accuracy.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Cost-Accuracy Analysis — GAIA Live Lane (Committed Evidence)",
        "",
        "Retrospective aggregation of the committed per-question telemetry from the",
        "GAIA live lane (`evals/reports/live_benchmarks/gaia_real/`). No new provider",
        "calls were made for this analysis.",
        "",
        "## Headline",
        "",
        f"- 20 questions, {total_tokens:,} tokens total, ~${total_cost:.2f} total.",
        f"- **Cost per correct answer: ~${per_correct_cost:.2f}** "
        f"({len(correct_rows)} correct answers).",
        "",
        "## Does Spending More Tokens Buy Correctness?",
        "",
        "| Group | Median tokens | Mean tokens | Median LLM calls | Median searches | Median wall (s) |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Correct ({len(correct_rows)}) | {tokens_by_correctness['correct']['median_tokens']:,} | "
        f"{tokens_by_correctness['correct']['mean_tokens']:,} | "
        f"{tokens_by_correctness['correct']['median_llm_calls']} | "
        f"{tokens_by_correctness['correct']['median_search_calls']} | "
        f"{tokens_by_correctness['correct']['median_wall_seconds']} |",
        f"| Incorrect ({len(incorrect_rows)}) | {tokens_by_correctness['incorrect']['median_tokens']:,} | "
        f"{tokens_by_correctness['incorrect']['mean_tokens']:,} | "
        f"{tokens_by_correctness['incorrect']['median_llm_calls']} | "
        f"{tokens_by_correctness['incorrect']['median_search_calls']} | "
        f"{tokens_by_correctness['incorrect']['median_wall_seconds']} |",
        f"| All ({len(rows)}) | {tokens_by_correctness['all']['median_tokens']:,} | "
        f"{tokens_by_correctness['all']['mean_tokens']:,} | "
        f"{tokens_by_correctness['all']['median_llm_calls']} | "
        f"{tokens_by_correctness['all']['median_search_calls']} | "
        f"{tokens_by_correctness['all']['median_wall_seconds']} |",
        "",
        "Splitting the 20 questions at the median token spend:",
        "",
        f"- Higher-spend half correct rate: {cost_correlation['higher_token_half_correct_rate']:.0%}",
        f"- Lower-spend half correct rate: {cost_correlation['lower_token_half_correct_rate']:.0%}",
        f"- Mean tokens correct vs incorrect: {cost_correlation['tokens_correct_vs_incorrect_ratio']}x",
        "",
        "Interpretation: correctness is not simply a matter of spending more — the",
        "failure taxonomy (critic crash, multi-hop gaps, wrong-fact selection) shows",
        "the budget was spent in different ways. The right lever is the agent's",
        "decision quality (which sources, which queries, which claims), which is",
        "exactly what the rerank layer, strict source policy, and the audit gate",
        "target. A live budget sweep (varying max_tool_calls / rounds on fixed",
        "questions) is the natural next experiment.",
        "",
        "See `cost_accuracy.json` for per-question rows.",
    ]
    OUT_DIR.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:1200])


if __name__ == "__main__":
    main()
