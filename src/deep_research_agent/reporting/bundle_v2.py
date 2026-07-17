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


class ReportBundleCompilerV2:
    """Compile only frozen, structurally auditable evidence into a V2 bundle."""

    def __init__(
        self,
        *,
        reducer: EvidenceReducer | None = None,
        auditor: EvidenceAuditor | None = None,
    ) -> None:
        self._reducer = reducer or EvidenceReducer()
        self._auditor = auditor or EvidenceAuditor()

    def compile(
        self,
        *,
        report_markdown: str,
        claims: Iterable[ClaimRecord],
        evidence_packets: Iterable[EvidencePacket],
        research_graph: ResearchGraph,
        sources: Iterable[ArtifactRef],
        corpus_manifest: CorpusManifest,
        run_manifest: Mapping[str, Any],
    ) -> ReportBundleV2:
        packets = list(evidence_packets)
        reduced = self._reducer.reduce(packets)
        claim_by_id = {claim.claim_id: claim for claim in reduced.claims}
        for claim in claims:
            existing = claim_by_id.get(claim.claim_id)
            if existing is not None and existing != claim:
                raise ValueError(f"conflicting claim definition for {claim.claim_id!r}")
            claim_by_id[claim.claim_id] = claim

        ordered_sources = self._deduplicate_sources([*reduced.artifacts, *sources])
        invalid_documents = self._invalid_source_documents(ordered_sources, corpus_manifest)
        audit = self._auditor.audit(
            claim_by_id.values(),
            corpus_manifest,
            invalid_document_reasons=invalid_documents,
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
        )

        supported = [*audit.accepted, *audit.qualified]
        evidence_matrix = {
            claim.claim_id: sorted({span.document_version_id for span in claim.evidence_spans})
            for claim in sorted(supported, key=lambda item: item.claim_id)
        }
        sanitized_report = self._rebuild_executive_summary(
            report_markdown,
            audit.executive_summary_claims,
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
        }
        return ReportBundleV2(
            report_markdown=sanitized_report,
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
            if current is None or source.artifact_id < current.artifact_id:
                source_by_content[source.content_sha256] = source
        return sorted(source_by_content.values(), key=lambda item: item.artifact_id)

    @staticmethod
    def _invalid_source_documents(
        sources: Iterable[ArtifactRef],
        manifest: CorpusManifest,
    ) -> dict[str, str]:
        invalid: dict[str, str] = {}
        for source in sources:
            document_version_id = source.metadata.get("document_version_id")
            if not isinstance(document_version_id, str):
                continue
            expected = manifest.content_hashes.get(document_version_id)
            if expected is not None and source.content_sha256 != expected:
                invalid[document_version_id] = "source_hash_mismatch"
        return invalid

    @staticmethod
    def _validate_graph_provenance(
        graph: ResearchGraph,
        *,
        evidence_spans: Mapping[str, EvidenceSpan],
        corpus_manifest: CorpusManifest,
    ) -> None:
        node_ids = [node.node_id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("research graph node ids must be unique")
        edge_ids = [edge.edge_id for edge in graph.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("research graph edge ids must be unique")
        known_nodes = set(node_ids)
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

    @staticmethod
    def _sorted_graph(graph: ResearchGraph) -> ResearchGraph:
        return ResearchGraph(
            nodes=sorted(graph.nodes, key=lambda item: item.node_id),
            edges=sorted(graph.edges, key=lambda item: item.edge_id),
        )

    @staticmethod
    def _rebuild_executive_summary(
        report_markdown: str,
        allowed_claims: Iterable[ClaimRecord],
    ) -> str:
        lines = report_markdown.splitlines()
        claims = [" ".join(claim.claim.split()) for claim in allowed_claims]
        rebuilt: list[str] = []
        index = 0
        found_summary = False
        while index < len(lines):
            line = lines[index]
            match = re.match(r"^(#{1,6})\s+executive summary\s*$", line.strip(), re.IGNORECASE)
            if match is None:
                rebuilt.append(line)
                index += 1
                continue

            found_summary = True
            summary_level = len(match.group(1))
            rebuilt.extend([line, ""])
            rebuilt.extend(f"- {claim}" for claim in claims)
            if claims:
                rebuilt.append("")
            index += 1
            while index < len(lines):
                next_heading = re.match(r"^(#{1,6})\s+", lines[index].strip())
                if next_heading is not None and len(next_heading.group(1)) <= summary_level:
                    break
                index += 1

        if not found_summary:
            return report_markdown
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
