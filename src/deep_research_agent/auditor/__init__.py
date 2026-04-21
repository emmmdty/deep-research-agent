"""Canonical auditor boundary."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AuditDecision",
    "ClaimRecord",
    "ClaimReviewQueue",
    "ClaimSupportEdgeRecord",
    "ConflictSetRecord",
    "CriticalClaimReviewItem",
    "EvidenceFragmentRecord",
    "claim_auditor_node",
]


def __getattr__(name: str):
    if name == "claim_auditor_node":
        return getattr(import_module("deep_research_agent.auditor.pipeline"), name)
    if name in {
        "AuditDecision",
        "ClaimRecord",
        "ClaimReviewQueue",
        "ClaimSupportEdgeRecord",
        "ConflictSetRecord",
        "CriticalClaimReviewItem",
        "EvidenceFragmentRecord",
    }:
        return getattr(import_module("deep_research_agent.auditor.models"), name)
    raise AttributeError(name)
