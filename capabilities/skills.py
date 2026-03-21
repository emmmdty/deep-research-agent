"""Claude Code 风格 skill 兼容加载。"""

from __future__ import annotations

import re
from pathlib import Path

from workflows.states import SkillDefinition


_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def load_skill_definitions(skill_paths: list[str]) -> list[SkillDefinition]:
    """从 skill 根目录列表中加载 SKILL.md。"""
    definitions: list[SkillDefinition] = []
    for root in [Path(path) for path in skill_paths if path]:
        if not root.exists():
            continue
        for skill_file in root.glob("*/SKILL.md"):
            parsed = _parse_skill_file(skill_file)
            if parsed is not None:
                definitions.append(parsed)
    return definitions


def _parse_skill_file(skill_file: Path) -> SkillDefinition | None:
    content = skill_file.read_text(encoding="utf-8")
    match = _FRONTMATTER_PATTERN.match(content)
    metadata: dict[str, str] = {}
    body = content
    if match:
        frontmatter, body = match.groups()
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("\"'")

    name = metadata.get("name") or skill_file.parent.name
    description = metadata.get("description", "")
    triggers = _extract_triggers(description=description, body=body)
    return SkillDefinition(
        name=name,
        description=description,
        path=str(skill_file.parent),
        body=body.strip(),
        triggers=triggers,
    )


def _extract_triggers(*, description: str, body: str) -> list[str]:
    text = f"{description}\n{body}".lower()
    candidates = [
        "installation",
        "setup",
        "requirements",
        "troubleshooting",
        "benchmark",
        "agent",
        "memory",
        "rag",
        "install",
        "教程",
        "安装",
        "依赖",
        "排查",
    ]
    return [token for token in candidates if token in text]
