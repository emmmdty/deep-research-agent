"""Reliability evaluation harness for the model-driven agent runtime.

Deterministic (zero provider tokens, zero network): scripted fakes stand in
for the model and the governed tools; every fault-injection scenario triggers
exactly one anomaly at one agent decision point and measures whether the
designed deterministic fallback absorbs it without changing the healthy path.
"""

from deep_research_agent.evals.reliability.agent_metrics import (
    format_report as format_agent_metrics_report,
)
from deep_research_agent.evals.reliability.agent_metrics import (
    run_metrics,
)
from deep_research_agent.evals.reliability.fault_injection import (
    ALL_SCENARIOS,
    CONTROL,
    Faults,
    Scenario,
    ScenarioResult,
    ScriptedChat,
    build_scripted_gateway,
    format_report,
    run_all,
    run_crash_resume,
)

__all__ = [
    "ALL_SCENARIOS",
    "CONTROL",
    "Faults",
    "Scenario",
    "ScenarioResult",
    "ScriptedChat",
    "build_scripted_gateway",
    "format_agent_metrics_report",
    "format_report",
    "run_all",
    "run_crash_resume",
    "run_metrics",
]
