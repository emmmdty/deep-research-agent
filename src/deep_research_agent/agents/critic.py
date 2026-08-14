"""Model-driven critic worker: contradiction review and report synthesis."""

from __future__ import annotations

from typing import Any

from loguru import logger

from deep_research_agent.agents.llm import LLMChat
from deep_research_agent.kernel.contracts import (
    ClaimRecord,
    EvidenceSpan,
    ResearchGraph,
    ResearchGraphEdge,
    ResearchGraphNode,
    TaskResult,
)
from deep_research_agent.orchestration.reducer import CriticDecision
from deep_research_agent.orchestration.workers import (
    TaskExecutionContext,
    WorkerOutput,
)

_MAX_SUMMARY_CLAIMS = 5
# The synthesis digest grows with parallel researcher outputs; keep a generous
# budget so long reports are not truncated mid-sentence.
_REPORT_MAX_TOKENS = 8192
_REVIEW_MAX_TOKENS = 8192


class LLMCriticWorker:
    """Critic agent: audits claim groups and synthesizes the final report.

    The critic receives every researcher output through the typed DAG dependency
    channel, asks the model to resolve contradictions and qualification, and then
    writes the reader-facing report markdown. Critic decisions only ever cite
    evidence spans that researchers actually emitted; anything else is treated
    as unresolved by the deterministic auditor.
    """

    def __init__(self, chat: LLMChat | None = None) -> None:
        self._chat = chat

    async def execute(self, task, context: TaskExecutionContext) -> WorkerOutput:
        chat = self._chat or LLMChat()
        packets = self._collect_packets(task, context)
        claims = [claim for packet in packets for claim in packet.claims]
        spans = [span for packet in packets for span in packet.evidence_spans]
        if not claims:
            raise RuntimeError(
                f"critic task {task.task_id!r} received no claims from any researcher task"
            )
        review = await self._review_claims(chat, task, context, claims, spans)
        decisions = [
            CriticDecision(
                decision_id=f"{context.job_id}:decision:{index:02d}",
                claim_ids=claim_ids,
                decision=str(decision.get("decision") or "qualified"),
                rationale_evidence_ids=tuple(
                    str(item) for item in decision.get("rationale_evidence_ids", [])
                ),
                rationale=str(decision.get("rationale") or "model review"),
            )
            for index, decision in enumerate(review.get("decisions", []), start=1)
            if isinstance(decision, dict)
            for claim_ids in [
                tuple(
                    str(item)
                    for item in decision.get("claim_ids", [])
                    if str(item)
                )
            ]
            if claim_ids
        ]
        try:
            report_markdown = await self._synthesize_report(
                chat, task, context, claims, spans, review
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "critic {}: model synthesis failed ({}); using deterministic report",
                task.task_id,
                exc,
            )
            report_markdown = self._deterministic_report(claims, task.objective)
        if not report_markdown.strip():
            logger.warning(
                "critic {}: model synthesis returned an empty report; using deterministic report",
                task.task_id,
            )
            report_markdown = self._deterministic_report(claims, task.objective)
        graph = self._build_graph(task, context, claims, spans)
        return WorkerOutput(
            result=TaskResult(
                task_id=task.task_id,
                job_id=task.job_id,
                status="completed",
            ),
            output={
                "task_id": task.task_id,
                "report_markdown": report_markdown,
                "research_graph": graph.model_dump(mode="json"),
                "claim_count": len(claims),
                "decision_count": len(decisions),
            },
            critic_decisions=decisions,
        )

    @staticmethod
    def _collect_packets(task, context: TaskExecutionContext) -> list[Any]:
        packets: list[Any] = []
        for dependency_id in sorted(context.dependency_results):
            dependency_output = context.dependency_results[dependency_id]
            result = getattr(dependency_output, "result", None)
            for packet in getattr(result, "evidence_packets", []) or []:
                packets.append(packet)
        return packets

    async def _review_claims(
        self,
        chat: LLMChat,
        task,
        context: TaskExecutionContext,
        claims: list[ClaimRecord],
        spans: list[EvidenceSpan],
    ) -> dict[str, Any]:
        span_index = {
            span.span_id: span.quote[:160] for span in spans
        }
        claim_digest = "\n".join(
            f"[{claim.claim_id}] critical={claim.critical} "
            f"status={claim.support_status} confidence={claim.confidence}\n"
            f"  {claim.claim}\n"
            f"  spans: {', '.join(span.span_id for span in claim.evidence_spans)}"
            for claim in sorted(claims, key=lambda item: item.claim_id)
        )
        span_digest = "\n".join(
            f"{span_id}: {quote}"
            for span_id, quote in sorted(span_index.items())
        )
        payload = await chat.chat_json(
            system=(
                "You are the critic agent of an evidence-first deep research "
                "system. Review the claims and their evidence spans. For each "
                "claim decide: accepted (fully supported), qualified (partially "
                "supported or hedged), contradicted (another claim or the "
                "evidence contradicts it), or unresolved (cannot tell). Contradicted "
                "and qualified claims MUST cite at least one rationale_evidence_id "
                "from the provided span ids. Respond with JSON only: "
                '{"decisions": [{"claim_ids": ["claim-id"], "decision": '
                '"accepted|qualified|contradicted|unresolved", '
                '"rationale_evidence_ids": ["span-id"], "rationale": "..."}]}'
            ),
            user=f"Claims:\n{claim_digest}\n\nEvidence spans:\n{span_digest}",
            max_tokens=_REVIEW_MAX_TOKENS,
            temperature=0.0,
        )
        known_span_ids = set(span_index)
        known_claim_ids = {claim.claim_id for claim in claims}
        for decision in payload.get("decisions", []):
            if not isinstance(decision, dict):
                continue
            decision["claim_ids"] = [
                claim_id
                for claim_id in decision.get("claim_ids", [])
                if claim_id in known_claim_ids
            ]
            decision["rationale_evidence_ids"] = [
                span_id
                for span_id in decision.get("rationale_evidence_ids", [])
                if span_id in known_span_ids
            ]
            decision_text = str(decision.get("decision") or "")
            if decision_text not in {"accepted", "qualified", "contradicted", "unresolved"}:
                decision["decision"] = "unresolved"
            if decision_text in {"contradicted", "qualified"} and not decision["rationale_evidence_ids"]:
                decision["decision"] = "unresolved"
                decision["rationale"] = (
                    "critic could not cite grounded evidence for its downgrade"
                )
        return payload

    async def _synthesize_report(
        self,
        chat: LLMChat,
        task,
        context: TaskExecutionContext,
        claims: list[ClaimRecord],
        spans: list[EvidenceSpan],
        review: dict[str, Any],
    ) -> str:
        claim_digest = "\n".join(
            f"[{claim.claim_id}] ({claim.support_status}, critical={claim.critical}) "
            f"{claim.claim}"
            for claim in sorted(claims, key=lambda item: item.claim_id)
        )
        decision_digest = "\n".join(
            f"{decision.get('decision')} -> {', '.join(map(str, decision.get('claim_ids', [])))}: "
            f"{decision.get('rationale', '')}"
            for decision in review.get("decisions", [])
            if isinstance(decision, dict)
        )
        markdown = await chat.chat(
            system=(
                "You are the writer of an evidence-first research report. Write a "
                "concise, well-structured Markdown report synthesizing ONLY the "
                "accepted and qualified claims. Preserve every claim's core fact; "
                "qualify anything hedged. The report must have sections: "
                "## Executive Summary (3-5 bullet findings), ## Findings "
                "(one subsection per finding), ## Evidence Status. Never introduce "
                "facts not present in the claims."
            ),
            user=f"Topic: {task.objective}\n\nClaims:\n{claim_digest}\n"
            f"\nCritic decisions:\n{decision_digest or '(none)'}",
            max_tokens=_REPORT_MAX_TOKENS,
            temperature=0.0,
        )
        return markdown.strip()

    @staticmethod
    def _deterministic_report(claims: list[ClaimRecord], objective: str) -> str:
        """Best-effort report compiled from grounded claims (model-free).

        Guarantees the critic always emits a report when claims exist, so a
        transient model failure cannot erase a completed research job.
        """

        lines = [
            f"# {objective}",
            "",
            "## Executive Summary",
            "",
        ]
        critical = [claim for claim in claims if claim.critical]
        for claim in (critical or claims)[:_MAX_SUMMARY_CLAIMS]:
            lines.append(f"- {claim.claim}")
        lines.extend(["", "## Findings", ""])
        for index, claim in enumerate(
            sorted(claims, key=lambda item: item.claim_id), start=1
        ):
            lines.append(
                f"{index}. ({claim.support_status}) {claim.claim}"
            )
        lines.extend(["", "## Evidence Status", ""])
        lines.append(
            f"- {len(claims)} grounded claims; "
            f"{sum(1 for c in claims if c.support_status == 'accepted')} accepted, "
            f"{sum(1 for c in claims if c.support_status == 'qualified')} qualified."
        )
        return "\n".join(lines)

    @staticmethod
    def _build_graph(
        task, context: TaskExecutionContext, claims: list[ClaimRecord], spans: list[EvidenceSpan]
    ) -> ResearchGraph:
        span_by_id = {span.span_id: span for span in spans}
        nodes: list[ResearchGraphNode] = []
        edges: list[ResearchGraphEdge] = []
        for index, claim in enumerate(sorted(claims, key=lambda item: item.claim_id), start=1):
            claim_node_id = f"claim-{index}"
            nodes.append(
                ResearchGraphNode(
                    node_id=claim_node_id,
                    kind="claim",
                    label=claim.claim,
                    properties={"support_status": claim.support_status, "critical": claim.critical},
                )
            )
            for span_index, span in enumerate(claim.evidence_spans, start=1):
                source_node_id = f"source-{index}-{span_index}"
                nodes.append(
                    ResearchGraphNode(
                        node_id=source_node_id,
                        kind="source",
                        label=span_by_id.get(span.span_id, span).section or span.document_version_id,
                        properties={"document_version_id": span.document_version_id},
                    )
                )
                edges.append(
                    ResearchGraphEdge(
                        edge_id=f"edge-{index}-{span_index}",
                        source_node_id=claim_node_id,
                        target_node_id=source_node_id,
                        relation="supported_by",
                        evidence_span_ids=[span.span_id],
                    )
                )
        return ResearchGraph(nodes=nodes, edges=edges)
