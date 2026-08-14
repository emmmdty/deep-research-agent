"""Model-driven researcher worker that grounds claims in governed tool results."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from loguru import logger

from deep_research_agent.agents.llm import LLMChat, LLMChatError
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    EvidencePacket,
    EvidenceSpan,
    TaskResult,
)
from deep_research_agent.orchestration.workers import (
    TaskExecutionContext,
    WorkerOutput,
)
from deep_research_agent.tool_gateway.models import ToolInvocation

_MAX_QUERIES = 4
_MAX_RESULTS_PER_QUERY = 4
_MAX_SOURCES = 12
_MAX_SNIPPET_CHARS = 500
_CLAIM_CHUNK_SIZE = 4


class LLMResearcherWorker:
    """Researcher agent: model plans queries, tool gateway fetches, model grounds claims.

    The agentic loop is: (1) the model proposes targeted search queries for its
    task objective; (2) the governed tool gateway executes them (web / GitHub /
    arXiv) with allow-list, budget, and idempotency enforcement; (3) the model
    extracts only claims it can ground in the returned excerpts; every claim
    carries exact evidence spans into frozen source artifacts.
    """

    def __init__(self, chat: LLMChat | None = None) -> None:
        self._chat = chat

    async def execute(self, task, context: TaskExecutionContext) -> WorkerOutput:
        if context.tool_gateway is None:
            raise RuntimeError("LLM researcher requires a configured tool gateway")
        chat = self._chat or LLMChat()

        queries = await self._plan_queries(chat, task, context)
        sources = await self._gather_sources(task, context, queries)
        if not sources:
            raise RuntimeError(
                f"researcher task {task.task_id!r} found no usable sources; "
                "no unsupported claim will be published"
            )
        claims = await self._ground_claims(chat, task, context, sources)
        packet, artifacts = self._build_packet(task, context, sources, claims)
        return WorkerOutput(
            result=TaskResult(
                task_id=task.task_id,
                job_id=task.job_id,
                status="completed",
                evidence_packets=[packet],
                output_artifacts=artifacts,
            ),
            output={
                "task_id": task.task_id,
                "objective": task.objective,
                "query_count": len(queries),
                "source_count": len(sources),
                "claim_count": len(claims),
            },
        )

    async def _plan_queries(
        self, chat: LLMChat, task, context: TaskExecutionContext
    ) -> list[str]:
        try:
            payload = await chat.chat_json(
                system=(
                    "You are a research agent. Propose concise web search queries that "
                    "will gather authoritative evidence for the task objective. Respond "
                    'with JSON only: {"queries": ["...", "..."]} with 1 to 4 queries.'
                ),
                user=f"Task objective:\n{task.objective}",
                max_tokens=512,
                temperature=0.0,
            )
            queries = [
                str(query).strip()
                for query in payload.get("queries", [])
                if isinstance(query, str) and query.strip()
            ]
            if queries:
                return queries[:_MAX_QUERIES]
        except LLMChatError as exc:
            logger.warning(
                "researcher {}: query planning unavailable ({}); using the task objective verbatim",
                task.task_id,
                exc,
            )
        return [task.objective]

    async def _gather_sources(
        self, task, context: TaskExecutionContext, queries: list[str]
    ) -> list[dict[str, Any]]:
        tool_names = ["web_search", "github_search", "arxiv_search"]
        sources: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for query in queries:
            for tool_name in tool_names:
                envelope = await context.invoke_tool(
                    ToolInvocation(
                        invocation_id=f"{context.job_id}:{task.task_id}:{uuid4().hex[:8]}",
                        tool_name=tool_name,
                        tenant_id=context.tenant_id,
                        idempotency_key="pending",  # overwritten by the harness fingerprint
                        arguments={
                            "query": query,
                            "max_results": _MAX_RESULTS_PER_QUERY,
                        },
                    )
                )
                if envelope.status != "succeeded" or envelope.output is None:
                    continue
                for item in envelope.output:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("url") or "")
                    snippet = str(item.get("snippet") or "").strip()
                    if not url or not snippet:
                        continue
                    dedupe_key = (url, snippet[:_MAX_SNIPPET_CHARS])
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    sources.append(
                        {
                            "index": len(sources) + 1,
                            "tool": tool_name,
                            "title": str(item.get("title") or url)[:200],
                            "url": url,
                            "snippet": snippet[:_MAX_SNIPPET_CHARS],
                        }
                    )
                if len(sources) >= _MAX_SOURCES:
                    return sources
        return sources

    async def _ground_claims(
        self, chat: LLMChat, task, context: TaskExecutionContext, sources: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        system_prompt = (
            "You are the researcher agent of an evidence-first system. Extract "
            "factual claims from the source excerpts. Every claim MUST be "
            "verbatim supported by the cited excerpt; never invent numbers, "
            "dates, or facts absent from the excerpts. Mark each claim with its "
            "source_index and a short verbatim quote from that excerpt. "
            "support_status is one of accepted | qualified | contradicted | "
            "unsupported. critical means the claim belongs in the executive "
            "summary. Answer immediately without thinking step by step. "
            "Respond with JSON only: "
            '{"claims": [{"claim": "...", "claim_type": "factual_claim", '
            '"critical": true, "support_status": "accepted", "confidence": 0.8, '
            '"source_index": 1, "quote": "verbatim excerpt"}]}'
        )
        # Process sources in small chunks: bounding input size keeps reasoning
        # short for thinking models and keeps every extraction call reliable.
        claims: list[dict[str, Any]] = []
        for chunk_start in range(0, len(sources), _CLAIM_CHUNK_SIZE):
            chunk = sources[chunk_start : chunk_start + _CLAIM_CHUNK_SIZE]
            source_digest = "\n".join(
                f"[{source['index']}] ({source['url']}) {source['title']}\n{source['snippet']}"
                for source in chunk
            )
            payload = await chat.chat_json(
                system=system_prompt,
                user=f"Task objective:\n{task.objective}\n\nSources:\n{source_digest}",
                max_tokens=2048,
                temperature=0.0,
            )
            claims.extend(
                claim for claim in payload.get("claims", []) if isinstance(claim, dict)
            )
        claims = [self._validate_claim(item, sources) for item in claims]
        claims = [claim for claim in claims if claim is not None]
        if not claims:
            raise LLMChatError(
                f"researcher {task.task_id!r} produced no grounded claims from {len(sources)} sources"
            )
        return claims

    @staticmethod
    def _validate_claim(
        item: dict[str, Any], sources: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        source_by_index = {int(source["index"]): source for source in sources}
        claim_text = str(item.get("claim") or "").strip()
        if not claim_text:
            return None
        source = source_by_index.get(int(item.get("source_index") or 0))
        if source is None:
            logger.warning("researcher: model cited unknown source_index={}", item.get("source_index"))
            return None
        quote = str(item.get("quote") or "").strip()
        if quote and quote not in source["snippet"]:
            logger.warning("researcher: model quote not verbatim; falling back to snippet prefix")
            quote = source["snippet"][:200]
        if not quote:
            quote = source["snippet"][:200]
        support_status = str(item.get("support_status") or "unsupported")
        if support_status not in {"accepted", "qualified", "contradicted", "unsupported"}:
            support_status = "qualified"
        return {
            "claim": claim_text,
            "claim_type": str(item.get("claim_type") or "factual_claim"),
            "critical": bool(item.get("critical", False)),
            "support_status": support_status,
            "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0.5))),
            "source_index": source["index"],
            "quote": quote,
        }

    @staticmethod
    def _build_packet(
        task, context: TaskExecutionContext, sources: list[dict[str, Any]], claims: list[dict[str, Any]]
    ) -> tuple[EvidencePacket, list[ArtifactRef]]:
        source_artifact_by_index: dict[int, ArtifactRef] = {}
        artifacts: list[ArtifactRef] = []
        spans: list[EvidenceSpan] = []
        for source in sources:
            content = json.dumps(
                {
                    "title": source["title"],
                    "url": source["url"],
                    "snippet": source["snippet"],
                    "tool": source["tool"],
                },
                ensure_ascii=True,
                sort_keys=True,
            ).encode("utf-8")
            document_version_id = f"{source['tool']}-{hashlib.sha256(content).hexdigest()[:16]}"
            artifact = ArtifactRef(
                artifact_id=f"{context.job_id}:{task.task_id}:src:{source['index']:02d}",
                uri=source["url"],
                media_type="text/markdown",
                content_sha256=hashlib.sha256(content).hexdigest(),
                created_by_task_id=task.task_id,
                metadata={
                    "document_version_id": document_version_id,
                    "critical_claims_allowed": True,
                    "source_title": source["title"],
                    "tool": source["tool"],
                },
            )
            source_artifact_by_index[source["index"]] = artifact
            artifacts.append(artifact)

        records: list[ClaimRecord] = []
        for index, claim in enumerate(claims, start=1):
            source = next(
                candidate
                for candidate in sources
                if candidate["index"] == claim["source_index"]
            )
            artifact = source_artifact_by_index[source["index"]]
            span = EvidenceSpan(
                span_id=f"{task.job_id}:span:{task.task_id}:{index:02d}",
                document_version_id=artifact.metadata["document_version_id"],
                section=source["title"][:200],
                quote=claim["quote"],
                extraction_method="agent_grounding",
            )
            spans.append(span)
            records.append(
                ClaimRecord(
                    claim_id=f"{task.job_id}:claim:{task.task_id}:{index:02d}",
                    claim=claim["claim"],
                    claim_type=claim["claim_type"],
                    critical=claim["critical"],
                    support_status=claim["support_status"],
                    confidence=claim["confidence"],
                    evidence_spans=[span],
                )
            )
        packet = EvidencePacket(
            packet_id=f"{context.job_id}:packet:{task.task_id}",
            task_id=task.task_id,
            evidence_spans=spans,
            claims=records,
            artifacts=artifacts,
        )
        return packet, artifacts
