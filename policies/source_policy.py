"""Source policy profile 与 enforcement。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from artifacts.schemas import validate_instance
from connectors.models import ConnectorCandidate
from connectors.utils import domain_from_uri
from policies.models import ConnectorBudget, SourcePolicyOverrides


POLICY_ROOT = Path(__file__).resolve().parent / "source-profiles"


class BlockedCandidate(BaseModel):
    """被 policy 拦截的 candidate。"""

    candidate: ConnectorCandidate = Field(description="被拦截 candidate")
    reason: str = Field(description="拦截原因")


class CandidateFilterResult(BaseModel):
    """candidate 过滤结果。"""

    allowed: list[ConnectorCandidate] = Field(default_factory=list)
    blocked: list[BlockedCandidate] = Field(default_factory=list)


class SourcePolicy(BaseModel):
    """已生效的 source policy。"""

    profile_name: str = Field(description="profile 名称")
    description: str = Field(default="", description="profile 描述")
    connectors: list[str] = Field(default_factory=list, description="允许 connector")
    connector_order: list[str] = Field(default_factory=list, description="connector 顺序")
    allow_domains: list[str] = Field(default_factory=list, description="允许域名")
    deny_domains: list[str] = Field(default_factory=list, description="禁止域名")
    auth_scopes: list[str] = Field(default_factory=lambda: ["public"], description="允许 auth scope")
    budget: ConnectorBudget = Field(default_factory=ConnectorBudget, description="预算")

    def with_overrides(self, overrides: SourcePolicyOverrides | dict[str, Any] | None) -> "SourcePolicy":
        """应用 job 级覆盖。"""
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
        """按 allow/deny 过滤 candidate。"""
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


def load_source_policy(profile_name: str) -> SourcePolicy:
    """加载预定义 source profile。"""
    path = POLICY_ROOT / f"{profile_name}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_instance("source-policy-profile", payload)
    return SourcePolicy.model_validate(payload)
