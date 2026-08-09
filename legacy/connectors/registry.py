"""Compatibility wrapper for the canonical connector registry."""

from deep_research_agent.connectors import registry as _registry
from deep_research_agent.connectors.registry import *  # noqa: F403

_web_fetch = _registry._web_fetch
