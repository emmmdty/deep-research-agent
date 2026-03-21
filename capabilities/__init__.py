"""能力注册与路由层。"""

from capabilities.registry import CapabilityRegistry, build_capability_registry
from capabilities.skills import load_skill_definitions

__all__ = [
    "CapabilityRegistry",
    "build_capability_registry",
    "load_skill_definitions",
]
