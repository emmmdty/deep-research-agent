"""Deterministic evidence audit for V2 claims."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Literal

from pydantic import ConfigDict, Field

from deep_research_agent.kernel.contracts import ClaimRecord, CorpusManifest, StrictModel
from deep_research_agent.orchestration.reducer import CriticDecision


AuditStatus = Literal["accepted", "qualified", "contradicted", "unsupported"]
SemanticJudge = Callable[[ClaimRecord], AuditStatus | None]


class EvidenceAuditResult(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: list[ClaimRecord] = Field(default_factory=list)
    qualified: list[ClaimRecord] = Field(default_factory=list)
    contradicted: list[ClaimRecord] = Field(default_factory=list)
    unsupported: list[ClaimRecord] = Field(default_factory=list)
    executive_summary_claims: list[ClaimRecord] = Field(default_factory=list)
    degradations: dict[str, str] = Field(default_factory=dict)
    unresolved_claim_ids: list[str] = Field(default_factory=list)


class EvidenceAuditor:
    """Apply frozen-corpus requirements before optional semantic enrichment."""

    def __init__(self, *, semantic_judge: SemanticJudge | None = None) -> None:
        self._semantic_judge = semantic_judge

    def audit(
        self,
        claims: Iterable[ClaimRecord],
        corpus_manifest: CorpusManifest,
        *,
        invalid_document_reasons: Mapping[str, str] | None = None,
        critic_decisions: Iterable[CriticDecision] = (),
        semantic_disagreements: Iterable[tuple[str, str]] = (),
        evidence_span_ids: Iterable[str] = (),
    ) -> EvidenceAuditResult:
        invalid_reasons = dict(invalid_document_reasons or {})
        frozen_ids = set(corpus_manifest.document_version_ids)
        buckets: dict[AuditStatus, list[ClaimRecord]] = {
            "accepted": [],
            "qualified": [],
            "contradicted": [],
            "unsupported": [],
        }
        degradations: dict[str, str] = {}
        claim_list = sorted(claims, key=lambda item: item.claim_id)
        claim_ids = {claim.claim_id for claim in claim_list}
        known_evidence_ids = {
            span.span_id for claim in claim_list for span in claim.evidence_spans
        }
        known_evidence_ids.update(evidence_span_ids)
        critic_by_claim: dict[str, CriticDecision] = {}
        unresolved_claim_ids = {
            claim_id for pair in semantic_disagreements for claim_id in pair
        }
        for decision in critic_decisions:
            valid_group = set(decision.claim_ids) <= claim_ids
            valid_rationale = bool(decision.rationale_evidence_ids) and set(
                decision.rationale_evidence_ids
            ) <= known_evidence_ids
            if not valid_group or not valid_rationale:
                unresolved_claim_ids.update(decision.claim_ids)
                continue
            if decision.unresolved or decision.decision == "unresolved":
                unresolved_claim_ids.update(decision.claim_ids)
                continue
            for claim_id in decision.claim_ids:
                critic_by_claim[claim_id] = decision

        for claim in claim_list:
            span_document_ids = {span.document_version_id for span in claim.evidence_spans}
            valid_ids = span_document_ids & frozen_ids - invalid_reasons.keys()
            outside_ids = span_document_ids - frozen_ids
            invalid_ids = span_document_ids & invalid_reasons.keys()

            if not valid_ids:
                status: AuditStatus = "unsupported"
                if invalid_ids:
                    reason = sorted(invalid_reasons[document_id] for document_id in invalid_ids)[0]
                elif outside_ids:
                    reason = "evidence_outside_frozen_corpus"
                else:
                    reason = "no_frozen_evidence"
                degradations[claim.claim_id] = reason
            elif outside_ids or invalid_ids:
                status = "qualified"
                degradations[claim.claim_id] = "evidence_partially_outside_frozen_corpus"
            else:
                status = claim.support_status

            decision = critic_by_claim.get(claim.claim_id)
            if decision is not None:
                status = self._apply_critic_decision(status, decision.decision)
            if claim.claim_id in unresolved_claim_ids:
                status = "unsupported" if claim.critical else "qualified"
                degradations[claim.claim_id] = "critic_unresolved"

            judged = self._semantic_judge(claim) if self._semantic_judge is not None else None
            status = self._apply_non_upgrading_judgment(status, judged)
            audited = claim.model_copy(update={"support_status": status})
            buckets[status].append(audited)

        executive = [
            claim
            for claim in (*buckets["accepted"], *buckets["qualified"])
            if claim.support_status in {"accepted", "qualified"}
        ]
        return EvidenceAuditResult(
            accepted=buckets["accepted"],
            qualified=buckets["qualified"],
            contradicted=buckets["contradicted"],
            unsupported=buckets["unsupported"],
            executive_summary_claims=sorted(executive, key=lambda item: item.claim_id),
            degradations={key: degradations[key] for key in sorted(degradations)},
            unresolved_claim_ids=sorted(unresolved_claim_ids & claim_ids),
        )

    @staticmethod
    def _apply_non_upgrading_judgment(
        deterministic: AuditStatus,
        judged: AuditStatus | None,
    ) -> AuditStatus:
        if judged is None or deterministic == "unsupported":
            return deterministic
        allowed_downgrades: dict[AuditStatus, set[AuditStatus]] = {
            "accepted": {"accepted", "qualified", "contradicted", "unsupported"},
            "qualified": {"qualified", "contradicted", "unsupported"},
            "contradicted": {"contradicted", "unsupported"},
            "unsupported": {"unsupported"},
        }
        return judged if judged in allowed_downgrades[deterministic] else deterministic

    @staticmethod
    def _apply_critic_decision(
        deterministic: AuditStatus,
        decision: Literal["accepted", "qualified", "contradicted"],
    ) -> AuditStatus:
        if deterministic == "unsupported":
            return deterministic
        if decision == "accepted":
            return "accepted" if deterministic == "accepted" else deterministic
        if decision == "qualified":
            return "qualified" if deterministic in {"accepted", "qualified"} else deterministic
        return "contradicted"
