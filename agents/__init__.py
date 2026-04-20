"""Agent 命名空间。

避免包级 eager import 放大循环依赖。
"""

__all__ = [
    "planner_node",
    "researcher_node",
    "verifier_node",
    "critic_node",
    "writer_node",
    "supervisor_node",
]


def __getattr__(name: str):
    if name == "planner_node":
        from agents.planner import planner_node

        return planner_node
    if name == "researcher_node":
        from agents.researcher import researcher_node

        return researcher_node
    if name == "verifier_node":
        from agents.verifier import verifier_node

        return verifier_node
    if name == "critic_node":
        from agents.critic import critic_node

        return critic_node
    if name == "writer_node":
        from agents.writer import writer_node

        return writer_node
    if name == "supervisor_node":
        from agents.supervisor import supervisor_node

        return supervisor_node
    raise AttributeError(name)
