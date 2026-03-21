"""Capability registry、skills 与 MCP 适配回归测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from workflows.states import TaskItem


def test_load_skill_definitions_parses_skill_md_frontmatter(tmp_path: Path):
    """应能从 Claude Code 风格的 SKILL.md 读取 skill 元数据。"""
    from capabilities.skills import load_skill_definitions

    skill_dir = tmp_path / "install-guide"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: install-guide
description: Improve installation and setup guidance.
---

# Install Guide

Use this skill for installation, setup, requirements, and troubleshooting tasks.
""",
        encoding="utf-8",
    )

    skills = load_skill_definitions([str(tmp_path)])

    assert len(skills) == 1
    assert skills[0].name == "install-guide"
    assert skills[0].description == "Improve installation and setup guidance."
    assert skills[0].path == str(skill_dir)


def test_capability_registry_combines_builtin_skill_and_mcp_capabilities(tmp_path: Path):
    """registry 应统一暴露 builtin / skill / mcp 三类能力。"""
    from capabilities.registry import build_capability_registry

    skill_dir = tmp_path / "skills" / "install-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: install-guide
description: Improve installation and setup guidance.
---

Use this skill for installation, setup, and troubleshooting.
""",
        encoding="utf-8",
    )

    settings = SimpleNamespace(
        enabled_sources=["web", "github", "arxiv"],
        enabled_capability_types=["builtin", "skill", "mcp"],
        skill_paths=[str(tmp_path / "skills")],
        mcp_servers=[
            {
                "name": "browser",
                "tools": [
                    {
                        "name": "browser.search",
                        "description": "Search docs and the web",
                    }
                ],
            }
        ],
    )

    registry = build_capability_registry(settings)
    names = [cap.name for cap in registry.list_all()]

    assert "web.search" in names
    assert "github.search" in names
    assert "arxiv.search" in names
    assert "skill.install-guide" in names
    assert "mcp.browser.search" in names


def test_capability_registry_prefers_skill_and_source_matched_tools_for_tutorial_task(
    tmp_path: Path,
):
    """教程类任务应优先路由到教程 skill 与 web/github 能力，而非 arxiv。"""
    from capabilities.registry import build_capability_registry

    skill_dir = tmp_path / "skills" / "install-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: install-guide
description: Improve installation and setup guidance.
---

Use this skill for installation, setup, requirements, and troubleshooting tasks.
""",
        encoding="utf-8",
    )

    settings = SimpleNamespace(
        enabled_sources=["web", "github", "arxiv"],
        enabled_capability_types=["builtin", "skill"],
        skill_paths=[str(tmp_path / "skills")],
        mcp_servers=[],
    )
    task = TaskItem(
        id=1,
        title="安装步骤与配置",
        intent="重点覆盖方面：编译或安装步骤",
        query="openclaw 安装步骤 tutorial setup guide",
        task_type="tutorial",
        expected_aspects=["编译或安装步骤"],
        preferred_sources=["web", "github"],
    )

    registry = build_capability_registry(settings)
    plan = registry.plan_for_task(task)
    plan_names = [cap.name for cap in plan]

    assert plan_names[0] == "skill.install-guide"
    assert "web.search" in plan_names
    assert "github.search" in plan_names
    assert "arxiv.search" not in plan_names
