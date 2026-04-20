"""Evaluation 命名空间。"""

__all__ = [
    "BenchmarkTopic",
    "ComparatorResult",
    "CostTracker",
    "LLMJudge",
    "evaluate_report",
    "get_tracker",
    "load_topics",
    "resolve_comparators",
    "run_comparator",
]


def __getattr__(name: str):
    if name in {"BenchmarkTopic", "ComparatorResult", "load_topics", "resolve_comparators", "run_comparator"}:
        from evaluation.comparators import (
            BenchmarkTopic,
            ComparatorResult,
            load_topics,
            resolve_comparators,
            run_comparator,
        )

        return {
            "BenchmarkTopic": BenchmarkTopic,
            "ComparatorResult": ComparatorResult,
            "load_topics": load_topics,
            "resolve_comparators": resolve_comparators,
            "run_comparator": run_comparator,
        }[name]
    if name == "evaluate_report":
        from evaluation.metrics import evaluate_report

        return evaluate_report
    if name == "LLMJudge":
        from evaluation.llm_judge import LLMJudge

        return LLMJudge
    if name in {"CostTracker", "get_tracker"}:
        from evaluation.cost_tracker import CostTracker, get_tracker

        return {"CostTracker": CostTracker, "get_tracker": get_tracker}[name]
    raise AttributeError(name)
