"""Source policy profile loading and enforcement."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from deep_research_agent.common import resolve_source_profile_name
from deep_research_agent.connectors.models import ConnectorCandidate
from deep_research_agent.connectors.utils import canonicalize_uri, domain_from_uri, fetch_uri_block_reason
from deep_research_agent.policy.models import ConnectorBudget, SourcePolicyOverrides
from deep_research_agent.reporting.schemas import validate_instance


PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLICY_ROOT = PROJECT_ROOT / "configs" / "source_profiles"


class BlockedCandidate(BaseModel):
    """Candidate blocked by source policy."""

    candidate: ConnectorCandidate = Field(description="Blocked candidate")
    reason: str = Field(description="Block reason")


class CandidateFilterResult(BaseModel):
    """Candidate filtering result."""

    allowed: list[ConnectorCandidate] = Field(default_factory=list)
    blocked: list[BlockedCandidate] = Field(default_factory=list)


class FetchPolicyDecision(BaseModel):
    """Pre-fetch URL safety decision."""

    allowed: bool = Field(description="Whether fetch is allowed")
    reason: str = Field(default="", description="Deny reason")
    canonical_uri: str = Field(default="", description="Canonical URI")


class SourcePolicy(BaseModel):
    """Resolved source policy."""

    profile_name: str = Field(description="Profile name")
    description: str = Field(default="", description="Profile description")
    connectors: list[str] = Field(default_factory=list, description="Allowed connectors")
    connector_order: list[str] = Field(default_factory=list, description="Connector order")
    allow_domains: list[str] = Field(default_factory=list, description="Allowed domains")
    deny_domains: list[str] = Field(default_factory=list, description="Denied domains")
    auth_scopes: list[str] = Field(default_factory=lambda: ["public"], description="Allowed auth scopes")
    budget: ConnectorBudget = Field(default_factory=ConnectorBudget, description="Budget")

    def with_overrides(self, overrides: SourcePolicyOverrides | dict[str, Any] | None) -> "SourcePolicy":
        """Apply job-level overrides."""
        if overrides is None:
            return self
        resolved = overrides if isinstance(overrides, SourcePolicyOverrides) else SourcePolicyOverrides.model_validate(overrides)
        payload = self.model_dump(mode="json")
        if resolved.allow_domains:
            payload["allow_domains"] = resolved.allow_domains
        if resolved.deny_domains:
            payload["deny_domains"] = resolved.deny_domains
        if resolved.budget is not None:
            payload["budget"] = resolved.budget.model_dump(mode="json")
        return SourcePolicy.model_validate(payload)

    def filter_candidates(self, candidates: list[ConnectorCandidate]) -> CandidateFilterResult:
        """Filter candidates by allow/deny domains."""
        allowed: list[ConnectorCandidate] = []
        blocked: list[BlockedCandidate] = []
        for candidate in candidates:
            domain = domain_from_uri(candidate.canonical_uri)
            if self.deny_domains and domain in self.deny_domains:
                blocked.append(BlockedCandidate(candidate=candidate, reason="domain_denied"))
                continue
            if self.allow_domains and domain not in self.allow_domains:
                blocked.append(BlockedCandidate(candidate=candidate, reason="domain_not_allowed"))
                continue
            allowed.append(candidate)
        return CandidateFilterResult(allowed=allowed[: self.budget.max_candidates_per_connector], blocked=blocked)

    def validate_fetch_uri(self, uri: str) -> FetchPolicyDecision:
        """Run URL safety and domain checks before fetch."""
        canonical_uri = canonicalize_uri(uri)
        block_reason = fetch_uri_block_reason(canonical_uri)
        if block_reason:
            return FetchPolicyDecision(allowed=False, reason=block_reason, canonical_uri=canonical_uri)
        domain = domain_from_uri(canonical_uri)
        if self.deny_domains and domain in self.deny_domains:
            return FetchPolicyDecision(allowed=False, reason="domain_denied", canonical_uri=canonical_uri)
        if self.allow_domains and domain not in self.allow_domains:
            return FetchPolicyDecision(allowed=False, reason="domain_not_allowed", canonical_uri=canonical_uri)
        return FetchPolicyDecision(allowed=True, canonical_uri=canonical_uri)


def load_source_policy(profile_name: str) -> SourcePolicy:
    """Load a predefined source profile."""
    resolved_profile_name = resolve_source_profile_name(profile_name)
    path = POLICY_ROOT / f"{resolved_profile_name}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_instance("source-policy-profile", payload)
    return SourcePolicy.model_validate(payload)
