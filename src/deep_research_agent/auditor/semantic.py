"""Deterministic evidence audit for V2 claims."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Literal

from pydantic import ConfigDict, Field

from deep_research_agent.auditor.span_matcher import build_verbatim_matcher, match_quotes
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    CorpusManifest,
    EvidenceSpan,
    StrictModel,
)
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
        evidence_spans: Iterable[EvidenceSpan] = (),
        source_artifacts: Iterable[ArtifactRef] = (),
        document_contents: Mapping[str, str] | None = None,
    ) -> EvidenceAuditResult:
        invalid_reasons = dict(invalid_document_reasons or {})
        frozen_ids = set(corpus_manifest.document_version_ids)
        document_texts = dict(document_contents or {})
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
        span_by_id = {
            span.span_id: span
            for span in (
                *evidence_spans,
                *(span for claim in claim_list for span in claim.evidence_spans),
            )
        }
        source_by_document: dict[str, ArtifactRef] = {}
        for source in source_artifacts:
            document_id = source.metadata.get("document_version_id")
            if not isinstance(document_id, str):
                continue
            expected = corpus_manifest.content_hashes.get(document_id)
            current = source_by_document.get(document_id)
            if current is None or (
                expected is not None
                and source.content_sha256 == expected
                and current.content_sha256 != expected
            ):
                source_by_document[document_id] = source
        decisions_by_claim: dict[str, list[CriticDecision]] = {}
        unresolved_claim_ids = {
            claim_id for pair in semantic_disagreements for claim_id in pair
        }
        for decision in critic_decisions:
            valid_group = set(decision.claim_ids) <= claim_ids
            valid_rationale = bool(decision.rationale_evidence_ids) and set(
                decision.rationale_evidence_ids
            ) <= known_evidence_ids
            valid_rationale = valid_rationale and all(
                (span := span_by_id.get(span_id)) is not None
                and span.document_version_id in frozen_ids
                and (source := source_by_document.get(span.document_version_id)) is not None
                and source.content_sha256 == corpus_manifest.content_hashes[span.document_version_id]
                for span_id in decision.rationale_evidence_ids
            )
            if not valid_group or not valid_rationale:
                unresolved_claim_ids.update(decision.claim_ids)
                continue
            if decision.unresolved or decision.decision == "unresolved":
                unresolved_claim_ids.update(decision.claim_ids)
                continue
            for claim_id in decision.claim_ids:
                decisions_by_claim.setdefault(claim_id, []).append(decision)

        critic_by_claim: dict[str, CriticDecision] = {}
        for claim_id, decisions in decisions_by_claim.items():
            if len(decisions) > 1:
                unresolved_claim_ids.add(claim_id)
                continue
            critic_by_claim[claim_id] = decisions[0]

        for claim in claim_list:
            span_document_ids = {span.document_version_id for span in claim.evidence_spans}
            valid_ids = span_document_ids & frozen_ids - invalid_reasons.keys()
            outside_ids = span_document_ids - frozen_ids
            invalid_ids = span_document_ids & invalid_reasons.keys()
            discovery_only_ids = {
                document_id
                for document_id in valid_ids
                if corpus_manifest.critical_claims_allowed.get(document_id) is not True
            }

            if claim.critical and discovery_only_ids:
                status: AuditStatus = "unsupported"
                degradations[claim.claim_id] = "critical_claim_source_not_allowed"
            elif not valid_ids:
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

            # Programmatic quote containment: when the frozen document text is
            # available, every evidence span must be an exact substring of it.
            # A quote the source never contained cannot ground the claim, so the
            # claim is degraded regardless of what the model self-reported. The
            # optional Aho-Corasick index batches the containment check per
            # document; without it, plain substring checks give the same result.
            if status in {"accepted", "qualified"}:
                uncontained: list[str] = []
                spans_by_document: dict[str, list[EvidenceSpan]] = {}
                for span in claim.evidence_spans:
                    spans_by_document.setdefault(span.document_version_id, []).append(span)
                for document_id, spans in spans_by_document.items():
                    text = document_texts.get(document_id)
                    if text is None:
                        continue
                    matcher = build_verbatim_matcher(span.quote for span in spans)
                    contained = match_quotes(
                        matcher,
                        [(span.span_id, span.quote) for span in spans],
                        text,
                    )
                    uncontained.extend(
                        span_id for span_id, is_contained in contained.items() if not is_contained
                    )
                if uncontained:
                    status = "unsupported" if claim.critical else "qualified"
                    degradations[claim.claim_id] = "quote_not_contained_in_document"

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
