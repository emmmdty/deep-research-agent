"""Deterministic structural reduction of typed evidence packets."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    EvidencePacket,
    EvidenceSpan,
    StrictModel,
)


class CriticDecision(StrictModel):
    """Typed semantic resolution for a group of related claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    claim_ids: tuple[str, ...] = Field(min_length=1)
    decision: Literal["accepted", "qualified", "contradicted", "unresolved"]
    rationale_evidence_ids: tuple[str, ...] = ()
    rationale: str = Field(min_length=1)
    unresolved: bool = False

    @model_validator(mode="after")
    def _validate_unresolved(self) -> CriticDecision:
        if self.unresolved != (self.decision == "unresolved"):
            raise ValueError("critic unresolved must match the decision status")
        return self


class ReducedEvidence(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    packet_ids: tuple[str, ...] = ()
    evidence_spans: tuple[EvidenceSpan, ...] = ()
    claims: tuple[ClaimRecord, ...] = ()
    artifacts: tuple[ArtifactRef, ...] = ()
    semantic_disagreements: list[tuple[str, str]] = Field(default_factory=list)
    critic_decisions: tuple[CriticDecision, ...] = ()


class EvidenceReducer:
    """Deduplicate exact records while leaving semantic judgment to a critic."""

    def reduce(
        self,
        packets: list[EvidencePacket] | tuple[EvidencePacket, ...],
        *,
        critic_decisions: list[CriticDecision] | tuple[CriticDecision, ...] = (),
    ) -> ReducedEvidence:
        packet_by_id: dict[str, EvidencePacket] = {}
        span_by_id: dict[str, EvidenceSpan] = {}
        claim_by_id: dict[str, ClaimRecord] = {}
        artifact_by_content: dict[str, ArtifactRef] = {}
        decision_by_id: dict[str, CriticDecision] = {}

        for packet in sorted(packets, key=lambda item: item.packet_id):
            self._add_exact(packet_by_id, packet.packet_id, packet, "packet")
            for span in packet.evidence_spans:
                self._add_exact(span_by_id, span.span_id, span, "evidence span")
            for claim in packet.claims:
                self._add_exact(claim_by_id, claim.claim_id, claim, "claim")
                for span in claim.evidence_spans:
                    self._add_exact(span_by_id, span.span_id, span, "evidence span")
            for artifact in packet.artifacts:
                current = artifact_by_content.get(artifact.content_sha256)
                if current is None or artifact.artifact_id < current.artifact_id:
                    artifact_by_content[artifact.content_sha256] = artifact
        for decision in sorted(critic_decisions, key=lambda item: item.decision_id):
            self._add_exact(decision_by_id, decision.decision_id, decision, "critic decision")

        claim_by_id = self._merge_semantic_duplicates(claim_by_id.values())
        disagreements: set[tuple[str, str]] = set()
        ordered_claims = sorted(claim_by_id.values(), key=lambda item: item.claim_id)
        resolved_pairs = {
            tuple(sorted((left, right)))
            for decision in decision_by_id.values()
            for index, left in enumerate(decision.claim_ids)
            for right in decision.claim_ids[index + 1 :]
        }
        for index, left in enumerate(ordered_claims):
            left_tokens = set(" ".join(left.claim.casefold().split()).split())
            for right in ordered_claims[index + 1 :]:
                right_tokens = set(" ".join(right.claim.casefold().split()).split())
                overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
                related = overlap >= 0.5 or (
                    left.claim.casefold() == right.claim.casefold()
                    and left.claim_type == right.claim_type
                )
                if related and (
                    left.support_status != right.support_status
                    or left.claim.casefold() != right.claim.casefold()
                ) and (left.claim_id, right.claim_id) not in resolved_pairs:
                    disagreements.add((left.claim_id, right.claim_id))

        return ReducedEvidence(
            packet_ids=tuple(sorted(packet_by_id)),
            evidence_spans=tuple(span_by_id[key] for key in sorted(span_by_id)),
            claims=tuple(claim_by_id[key] for key in sorted(claim_by_id)),
            artifacts=tuple(sorted(artifact_by_content.values(), key=lambda item: item.artifact_id)),
            semantic_disagreements=sorted(disagreements),
            critic_decisions=tuple(decision_by_id[key] for key in sorted(decision_by_id)),
        )

    @staticmethod
    def _add_exact(target: dict, key: str, value, label: str) -> None:
        existing = target.get(key)
        if existing is not None and existing != value:
            raise ValueError(f"conflicting {label} definition for {key!r}")
        target[key] = value

    @staticmethod
    def _merge_semantic_duplicates(claims) -> dict[str, ClaimRecord]:
        groups: dict[tuple[str, str, str, bool], list[ClaimRecord]] = defaultdict(list)
        for claim in claims:
            key = (
                " ".join(claim.claim.casefold().split()),
                claim.claim_type,
                claim.support_status,
                claim.critical,
            )
            groups[key].append(claim)

        merged: dict[str, ClaimRecord] = {}
        for related in groups.values():
            ordered = sorted(related, key=lambda item: item.claim_id)
            canonical = ordered[0]
            span_by_id: dict[str, EvidenceSpan] = {}
            for claim in ordered:
                for span in claim.evidence_spans:
                    existing = span_by_id.get(span.span_id)
                    if existing is not None and existing != span:
                        raise ValueError(
                            f"conflicting evidence span definition for {span.span_id!r}"
                        )
                    span_by_id[span.span_id] = span
            merged[canonical.claim_id] = canonical.model_copy(
                update={
                    "confidence": max(claim.confidence for claim in ordered),
                    "evidence_spans": [span_by_id[key] for key in sorted(span_by_id)],
                }
            )
        return merged
