"""Deterministic compiler and compatibility loader for report bundle V2."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from deep_research_agent.auditor.semantic import EvidenceAuditor
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    CorpusManifest,
    EvidencePacket,
    EvidenceSpan,
    ReportBundleV2,
    ResearchGraph,
)
from deep_research_agent.orchestration.reducer import EvidenceReducer
from deep_research_agent.orchestration.reducer import CriticDecision
from deep_research_agent.reporting.citations import CitationInjector


class ReportBundleCompilerV2:
    """Compile only frozen, structurally auditable evidence into a V2 bundle."""

    def __init__(
        self,
        *,
        reducer: EvidenceReducer | None = None,
        auditor: EvidenceAuditor | None = None,
        citations: CitationInjector | None = None,
    ) -> None:
        self._reducer = reducer or EvidenceReducer()
        self._auditor = auditor or EvidenceAuditor()
        self._citations = citations or CitationInjector()

    def compile(
        self,
        *,
        report_markdown: str,
        claims: Iterable[ClaimRecord],
        evidence_packets: Iterable[EvidencePacket],
        critic_decisions: Iterable[CriticDecision] = (),
        research_graph: ResearchGraph,
        sources: Iterable[ArtifactRef],
        corpus_manifest: CorpusManifest,
        run_manifest: Mapping[str, Any],
        citation_verification: Mapping[str, Any] | None = None,
    ) -> ReportBundleV2:
        packets = list(evidence_packets)
        critic_decisions = list(critic_decisions)
        reduced = self._reducer.reduce(packets, critic_decisions=critic_decisions)
        claim_by_id = {claim.claim_id: claim for claim in reduced.claims}
        merged_texts = {
            (claim.claim.casefold(), claim.claim_type, claim.support_status, claim.critical)
            for claim in reduced.claims
        }
        for claim in claims:
            existing = claim_by_id.get(claim.claim_id)
            if existing is not None and existing != claim:
                # The reduced claim is authoritative: semantic dedup may have
                # merged identical claims across parallel tasks and attached the
                # union of their evidence spans (text/status never change).
                merged_spans = {span.span_id for span in existing.evidence_spans}
                if (
                    existing.claim != claim.claim
                    or existing.support_status != claim.support_status
                    or not {span.span_id for span in claim.evidence_spans} <= merged_spans
                ):
                    raise ValueError(
                        f"conflicting claim definition for {claim.claim_id!r}"
                    )
                continue
            if (
                claim.claim.casefold(),
                claim.claim_type,
                claim.support_status,
                claim.critical,
            ) in merged_texts:
                # Identical to a sibling that semantic dedup merged away; keep
                # the canonical merged claim only.
                continue
            claim_by_id[claim.claim_id] = claim

        ordered_sources = self._deduplicate_sources([*reduced.artifacts, *sources])
        invalid_documents = self._invalid_source_documents(ordered_sources, corpus_manifest)
        document_contents = {
            document_id: source.metadata["source_text"]
            for source in ordered_sources
            if (document_id := source.metadata.get("document_version_id")) is not None
            and isinstance(source.metadata.get("source_text"), str)
        }
        audit = self._auditor.audit(
            claim_by_id.values(),
            corpus_manifest,
            invalid_document_reasons=invalid_documents,
            critic_decisions=reduced.critic_decisions,
            semantic_disagreements=reduced.semantic_disagreements,
            evidence_span_ids=(span.span_id for span in reduced.evidence_spans),
            evidence_spans=(
                *reduced.evidence_spans,
                *(span for claim in claim_by_id.values() for span in claim.evidence_spans),
            ),
            source_artifacts=ordered_sources,
            document_contents=document_contents,
        )
        span_by_id: dict[str, EvidenceSpan] = {}
        for span in (
            *reduced.evidence_spans,
            *(span for claim in claim_by_id.values() for span in claim.evidence_spans),
        ):
            existing = span_by_id.get(span.span_id)
            if existing is not None and existing != span:
                raise ValueError(f"conflicting evidence span definition for {span.span_id!r}")
            span_by_id[span.span_id] = span
        self._validate_graph_provenance(
            research_graph,
            evidence_spans=span_by_id,
            corpus_manifest=corpus_manifest,
            sources=ordered_sources,
        )

        supported = [*audit.accepted, *audit.qualified]
        evidence_matrix = {
            claim.claim_id: sorted({span.document_version_id for span in claim.evidence_spans})
            for claim in sorted(supported, key=lambda item: item.claim_id)
        }
        sanitized_report = self._rebuild_executive_summary(
            report_markdown,
            self._top_executive_summary_claims(audit.executive_summary_claims),
        )
        citation_result = self._citations.inject(
            sanitized_report,
            supported,
            span_by_id.values(),
            ordered_sources,
        )
        audit_summary = {
            "accepted_claim_ids": [claim.claim_id for claim in audit.accepted],
            "qualified_claim_ids": [claim.claim_id for claim in audit.qualified],
            "contradicted_claim_ids": [claim.claim_id for claim in audit.contradicted],
            "unsupported_claim_ids": [claim.claim_id for claim in audit.unsupported],
            "executive_summary_claim_ids": [
                claim.claim_id for claim in audit.executive_summary_claims
            ],
            "degradations": audit.degradations,
            "semantic_disagreements": reduced.semantic_disagreements,
            "unresolved_claim_ids": audit.unresolved_claim_ids,
            "report_citation_coverage": citation_result.coverage,
            "citation_verification": citation_verification or {},
        }
        return ReportBundleV2(
            report_markdown=citation_result.markdown,
            accepted_claims=audit.accepted,
            qualified_claims=audit.qualified,
            evidence_matrix=evidence_matrix,
            research_graph=self._sorted_graph(research_graph),
            sources=ordered_sources,
            audit_summary=audit_summary,
            corpus_manifest=corpus_manifest,
            run_manifest=self._canonical_mapping(run_manifest),
        )

    @staticmethod
    def to_canonical_json(bundle: ReportBundleV2) -> str:
        return json.dumps(
            bundle.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _deduplicate_sources(sources: Iterable[ArtifactRef]) -> list[ArtifactRef]:
        source_by_id: dict[str, ArtifactRef] = {}
        for source in sources:
            existing = source_by_id.get(source.artifact_id)
            if existing is not None and existing != source:
                raise ValueError(f"conflicting source definition for {source.artifact_id!r}")
            source_by_id[source.artifact_id] = source
        source_by_content: dict[str, ArtifactRef] = {}
        for source in source_by_id.values():
            current = source_by_content.get(source.content_sha256)
            source_has_document = isinstance(source.metadata.get("document_version_id"), str)
            current_has_document = current is not None and isinstance(
                current.metadata.get("document_version_id"), str
            )
            if current is None or (source_has_document and not current_has_document) or (
                source_has_document == current_has_document and source.artifact_id < current.artifact_id
            ):
                source_by_content[source.content_sha256] = source
        return sorted(source_by_content.values(), key=lambda item: item.artifact_id)

    @staticmethod
    def _invalid_source_documents(
        sources: Iterable[ArtifactRef],
        manifest: CorpusManifest,
    ) -> dict[str, str]:
        source_list = list(sources)
        invalid: dict[str, str] = {}
        supplied_documents: set[str] = set()
        for source in source_list:
            document_version_id = source.metadata.get("document_version_id")
            if not isinstance(document_version_id, str):
                continue
            supplied_documents.add(document_version_id)
            expected = manifest.content_hashes.get(document_version_id)
            if expected is not None and source.content_sha256 != expected:
                invalid[document_version_id] = "source_hash_mismatch"
        for document_version_id in manifest.document_version_ids:
            matching = [
                source
                for source in source_list
                if source.metadata.get("document_version_id") == document_version_id
                and source.content_sha256 == manifest.content_hashes[document_version_id]
            ]
            if matching:
                invalid.pop(document_version_id, None)
            elif document_version_id not in supplied_documents:
                invalid[document_version_id] = "missing_source_artifact"
            else:
                invalid[document_version_id] = "source_hash_mismatch"
        return invalid

    @staticmethod
    def _validate_graph_provenance(
        graph: ResearchGraph,
        *,
        evidence_spans: Mapping[str, EvidenceSpan],
        corpus_manifest: CorpusManifest,
        sources: Iterable[ArtifactRef],
    ) -> None:
        node_ids = [node.node_id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("research graph node ids must be unique")
        edge_ids = [edge.edge_id for edge in graph.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("research graph edge ids must be unique")
        known_nodes = set(node_ids)
        source_by_document: dict[str, ArtifactRef] = {}
        for source in sources:
            document_id = source.metadata.get("document_version_id")
            if not isinstance(document_id, str):
                continue
            current = source_by_document.get(document_id)
            expected = corpus_manifest.content_hashes.get(document_id)
            if current is None or (
                expected is not None
                and source.content_sha256 == expected
                and current.content_sha256 != expected
            ):
                source_by_document[document_id] = source
        for edge in graph.edges:
            if edge.source_node_id not in known_nodes or edge.target_node_id not in known_nodes:
                raise ValueError(f"graph edge {edge.edge_id} references an unknown node")
            if not edge.evidence_span_ids:
                raise ValueError(f"graph edge {edge.edge_id} requires exact evidence provenance")
            unknown = set(edge.evidence_span_ids) - evidence_spans.keys()
            if unknown:
                raise ValueError(f"graph edge {edge.edge_id} references unknown evidence spans")
            outside = {
                evidence_spans[span_id].document_version_id
                for span_id in edge.evidence_span_ids
            } - set(corpus_manifest.document_version_ids)
            if outside:
                raise ValueError(f"graph edge {edge.edge_id} references evidence outside frozen corpus")
            missing_artifacts = {
                evidence_spans[span_id].document_version_id
                for span_id in edge.evidence_span_ids
                if evidence_spans[span_id].document_version_id not in source_by_document
            }
            if missing_artifacts:
                raise ValueError(
                    f"graph edge {edge.edge_id} references evidence without a source artifact"
                )
            mismatched_artifacts = {
                document_id
                for document_id in {
                    evidence_spans[span_id].document_version_id for span_id in edge.evidence_span_ids
                }
                if source_by_document[document_id].content_sha256
                != corpus_manifest.content_hashes[document_id]
            }
            if mismatched_artifacts:
                raise ValueError(f"graph edge {edge.edge_id} references a source hash mismatch")

    @staticmethod
    def _sorted_graph(graph: ResearchGraph) -> ResearchGraph:
        return ResearchGraph(
            nodes=sorted(graph.nodes, key=lambda item: item.node_id),
            edges=sorted(graph.edges, key=lambda item: item.edge_id),
        )

    @staticmethod
    def _summary_heading_at(lines: list[str], index: int) -> tuple[int, int] | None:
        line = lines[index].strip()
        atx = re.fullmatch(
            r"(#{1,6})[ \t]+executive[ \t]+summary(?:[ \t]*:[ \t]*)?(?:[ \t]+#+[ \t]*)?",
            line,
            re.IGNORECASE,
        )
        if atx is not None:
            return len(atx.group(1)), 1
        if index + 1 >= len(lines):
            return None
        setext = re.fullmatch(
            r"executive[ \t]+summary(?:[ \t]*:[ \t]*)?(?:[ \t]+#+[ \t]*)?",
            line,
            re.IGNORECASE,
        )
        underline = re.fullmatch(r"[=-]{3,}", lines[index + 1].strip())
        if setext is not None and underline is not None:
            return (1 if underline.group(0)[0] == "=" else 2), 2
        return None

    @staticmethod
    def _markdown_heading_level(lines: list[str], index: int) -> int | None:
        line = lines[index].strip()
        atx = re.match(r"^(#{1,6})[ \t]+", line)
        if atx is not None:
            return len(atx.group(1))
        if index + 1 < len(lines) and line:
            underline = re.fullmatch(r"[=-]{3,}", lines[index + 1].strip())
            if underline is not None:
                return 1 if underline.group(0)[0] == "=" else 2
        return None

    @staticmethod
    def _top_executive_summary_claims(
        claims: Iterable[ClaimRecord],
        *,
        cap: int = 5,
    ) -> list[ClaimRecord]:
        """Pick the readable executive-summary subset: critical first, then id.

        The auditor passes every supported claim through; rendering them all as
        summary bullets produces a bullet dump that buries the findings. The
        cap mirrors the critic's synthesis guidance (3-5 summary bullets).
        """
        selected = sorted(claims, key=lambda claim: (not claim.critical, claim.claim_id))
        return selected[:cap]

    @staticmethod
    def _rebuild_executive_summary(
        report_markdown: str,
        allowed_claims: Iterable[ClaimRecord],
    ) -> str:
        lines = report_markdown.splitlines()
        claims = [" ".join(claim.claim.split()) for claim in allowed_claims]
        rebuilt: list[str] = []
        index = 0
        summary_matches = [
            (line_index, heading)
            for line_index in range(len(lines))
            if (heading := ReportBundleCompilerV2._summary_heading_at(lines, line_index)) is not None
        ]
        if len(summary_matches) > 1:
            raise ValueError("ambiguous executive summary headings")
        found_summary = bool(summary_matches)
        while index < len(lines):
            heading = ReportBundleCompilerV2._summary_heading_at(lines, index)
            if heading is None:
                line = lines[index]
                rebuilt.append(line)
                index += 1
                continue

            found_summary = True
            summary_level, consumed_lines = heading
            rebuilt.extend(["## Executive Summary", ""])
            rebuilt.extend(f"- {claim}" for claim in claims)
            if claims:
                rebuilt.append("")
            index += consumed_lines
            while index < len(lines):
                next_heading_level = ReportBundleCompilerV2._markdown_heading_level(lines, index)
                if next_heading_level is not None and next_heading_level <= summary_level:
                    break
                index += 1

        if not found_summary:
            prefix = ["## Executive Summary", ""]
            prefix.extend(f"- {claim}" for claim in claims)
            if claims:
                prefix.append("")
            prefix.extend(lines)
            suffix = "\n" if report_markdown.endswith("\n") else ""
            return "\n".join(prefix) + suffix
        suffix = "\n" if report_markdown.endswith("\n") else ""
        return "\n".join(rebuilt) + suffix

    @classmethod
    def _canonical_mapping(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        return json.loads(
            json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )


def load_report_bundle(path: str | Path) -> ReportBundleV2 | dict[str, Any]:
    """Validate V2 bundles while preserving reads of legacy artifact shapes."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("schema_version") == "2.0":
        return ReportBundleV2.model_validate(payload)
    if not isinstance(payload, dict):
        raise ValueError("report bundle must be a JSON object")
    return payload
