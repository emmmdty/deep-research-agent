"""工作流命名空间。"""

__all__ = [
    "build_research_graph",
    "run_research",
    "ResearchState",
    "TaskItem",
    "CriticFeedback",
]


def __getattr__(name: str):
    if name in {"build_research_graph", "run_research"}:
        from legacy.workflows.graph import build_research_graph, run_research

        return {
            "build_research_graph": build_research_graph,
            "run_research": run_research,
        }[name]
    if name in {"ResearchState", "TaskItem", "CriticFeedback"}:
        from legacy.workflows.states import CriticFeedback, ResearchState, TaskItem

        return {
            "ResearchState": ResearchState,
            "TaskItem": TaskItem,
            "CriticFeedback": CriticFeedback,
        }[name]
    raise AttributeError(name)
