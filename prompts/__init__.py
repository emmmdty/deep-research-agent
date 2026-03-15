"""提示词模板管理模块。"""

from prompts.templates import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT,
    SUMMARIZER_SYSTEM_PROMPT,
    SUMMARIZER_USER_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    CRITIC_USER_PROMPT,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_PROMPT,
)
from prompts.project_audit import (
    V1_PROJECT_AUDIT_PROMPT,
    build_v1_project_audit_prompt,
)

__all__ = [
    "PLANNER_SYSTEM_PROMPT",
    "PLANNER_USER_PROMPT",
    "SUMMARIZER_SYSTEM_PROMPT",
    "SUMMARIZER_USER_PROMPT",
    "CRITIC_SYSTEM_PROMPT",
    "CRITIC_USER_PROMPT",
    "WRITER_SYSTEM_PROMPT",
    "WRITER_USER_PROMPT",
    "V1_PROJECT_AUDIT_PROMPT",
    "build_v1_project_audit_prompt",
]
