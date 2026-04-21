"""统一能力注册表与任务路由。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from capabilities.mcp import build_mcp_capabilities
from capabilities.skills import load_skill_definitions
from legacy.workflows.states import TaskItem, ToolCapability


@dataclass
class CapabilityRegistry:
    """统一能力注册表。"""

    capabilities: list[ToolCapability]

    def list_all(self) -> list[ToolCapability]:
        return list(self.capabilities)

    def plan_for_task(
        self,
        task: TaskItem,
        *,
        missing_aspects: list[str] | None = None,
        failure_context: dict | None = None,
    ) -> list[ToolCapability]:
        """按任务类型和触发词排序能力。"""
        scored: list[tuple[int, ToolCapability]] = []
        text = f"{task.title} {task.intent} {task.query} {' '.join(task.expected_aspects)}".lower()
        preferred_builtin = {
            source_name for source_name in (task.preferred_sources or [])
        }
        missing_text = " ".join(missing_aspects or []).lower()
        failure_context = failure_context or {}

        for capability in self.capabilities:
            score = capability.priority
            if capability.kind == "builtin":
                if capability.metadata.get("source_name") in preferred_builtin:
                    score += 100
                if task.task_type == "tutorial" and capability.metadata.get("source_name") == "arxiv":
                    score -= 100
            if capability.kind == "skill":
                triggers = capability.metadata.get("triggers", [])
                score += 120 if any(trigger in text for trigger in triggers) else 0
            if capability.kind == "mcp":
                if task.task_type in {"tutorial", "comparison"}:
                    score += 30
                if "docs" in capability.name or "search" in capability.name:
                    score += 15
            if missing_text and any(token in missing_text for token in capability.tags):
                score += 20
            if failure_context.get("quality_gate_status") == "failed" and capability.kind in {"skill", "mcp"}:
                score += 10
            scored.append((score, capability))

        planned = [cap for _, cap in sorted(scored, key=lambda item: item[0], reverse=True)]
        filtered = [
            cap
            for cap in planned
            if cap.kind != "builtin" or cap.metadata.get("source_name") in preferred_builtin or cap.metadata.get("source_name") == "web"
        ]
        return _dedupe_capabilities(filtered)


def build_capability_registry(settings) -> CapabilityRegistry:
    """从 settings 构建完整 registry。"""
    capability_types = set(getattr(settings, "enabled_capability_types", ["builtin", "skill", "mcp"]))
    capabilities: list[ToolCapability] = []
    if "builtin" in capability_types:
        capabilities.extend(_builtin_capabilities(getattr(settings, "enabled_sources", [])))
    if "skill" in capability_types:
        for definition in load_skill_definitions(getattr(settings, "skill_paths", [])):
            capabilities.append(
                ToolCapability(
                    name=f"skill.{definition.name}",
                    kind="skill",
                    description=definition.description,
                    tags=["skill", *definition.triggers],
                    priority=120,
                    metadata={
                        "path": definition.path,
                        "body": definition.body,
                        "triggers": definition.triggers,
                    },
                )
            )
    if "mcp" in capability_types:
        capabilities.extend(
            build_mcp_capabilities(
                getattr(settings, "mcp_servers", []),
                config_path=getattr(settings, "mcp_config_path", None),
                workspace_dir=getattr(settings, "workspace_dir", "workspace"),
            )
        )
    return CapabilityRegistry(capabilities=_dedupe_capabilities(capabilities))


def _builtin_capabilities(enabled_sources: Iterable[str]) -> list[ToolCapability]:
    all_capabilities = {
        "web": ToolCapability(
            name="web.search",
            kind="builtin",
            description="网页搜索",
            source_type="web",
            tags=["search", "web"],
            priority=80,
            metadata={"source_name": "web"},
        ),
        "github": ToolCapability(
            name="github.search",
            kind="builtin",
            description="GitHub 搜索",
            source_type="github",
            tags=["search", "github"],
            priority=80,
            metadata={"source_name": "github"},
        ),
        "arxiv": ToolCapability(
            name="arxiv.search",
            kind="builtin",
            description="arXiv 检索",
            source_type="arxiv",
            tags=["search", "paper"],
            priority=70,
            metadata={"source_name": "arxiv"},
        ),
    }
    return [all_capabilities[source] for source in enabled_sources if source in all_capabilities]


def _dedupe_capabilities(capabilities: Iterable[ToolCapability]) -> list[ToolCapability]:
    deduped: dict[str, ToolCapability] = {}
    for capability in capabilities:
        deduped[capability.name] = capability
    return list(deduped.values())
