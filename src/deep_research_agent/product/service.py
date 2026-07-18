"""Application service for tenant-scoped research product workflows."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from deep_research_agent.domain_packs.registry import DomainPackRegistry
from deep_research_agent.kernel.contracts import ResearchBrief
from deep_research_agent.orchestration.dag import ResearchPlanner
from deep_research_agent.product.auth import AuthService
from deep_research_agent.product.db import ProductDatabase
from deep_research_agent.product.repositories import ProductRepository
from deep_research_agent.product.tables import (
    ConversationTable,
    CorpusDocumentTable,
    MemoryTable,
    MessageTable,
    ModelEndpointTable,
    RunEventTable,
    RunTable,
    RuntimeConfigTable,
    ToolConfigTable,
    TopicTable,
)
from deep_research_agent.research_jobs import ResearchJobService


TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})
MEMORY_SCOPES = frozenset(
    {"run_state", "conversation_focus", "user_memory", "topic_memory", "agent_experience"}
)
_HIGH_COST_MARKERS = (
    "every paper",
    "all papers",
    "exhaustive",
    "ever published",
    "the entire internet",
    "everything about",
)
_SECRET_KEY_MARKERS = (
    "apikey",
    "secret",
    "password",
    "token",
    "credential",
    "authorization",
    "privatekey",
    "accesskey",
    "bearer",
    "clientkey",
    "signingkey",
    "sshkey",
)
_SAFE_CREDENTIAL_REFERENCE_SUFFIXES = ("credentialid", "credentialids")
_SAFE_TOKEN_BUDGET_SUFFIXES = ("tokenbudget", "tokenlimit", "tokencount", "tokenusage", "maxtokens")
_FOLLOW_UP_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "analyze",
        "compare",
        "for",
        "in",
        "of",
        "on",
        "research",
        "summarize",
        "the",
        "this",
        "to",
        "update",
        "with",
    }
)


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(16)}"


def _iso(value: datetime) -> str:
    return value.isoformat()


def _is_secret_key(key: Any, value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).casefold())
    if normalized.endswith(_SAFE_CREDENTIAL_REFERENCE_SUFFIXES):
        return False
    if normalized.endswith(_SAFE_TOKEN_BUDGET_SUFFIXES) and isinstance(value, (int, float)):
        return False
    return any(marker in normalized for marker in _SECRET_KEY_MARKERS)


def redact_secrets(value: Any) -> Any:
    """Recursively redact common secret-bearing configuration fields."""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key, item):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_secret_key(key, item):
                return True
            if _contains_secret_key(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_secret_key(item) for item in value)
    return False


class ProductService:
    """Repository-backed product behavior independent of HTTP concerns."""

    def __init__(
        self,
        database: ProductDatabase,
        *,
        runtime_service: ResearchJobService,
        start_worker_by_default: bool | None = None,
    ) -> None:
        self.database = database
        self.repository = ProductRepository(database.sessions)
        self.auth = AuthService(self.repository)
        self.runtime_service = runtime_service
        self.start_worker_by_default = (
            not database.offline_mode
            if start_worker_by_default is None
            else bool(start_worker_by_default)
        )

    def bootstrap_admin(self, *, email: str, password: str) -> dict[str, Any]:
        return self.user_dict(self.auth.bootstrap_admin(email=email, password=password))

    @staticmethod
    def user_dict(user: Any) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "role": user.role,
        }

    def create_topic(self, *, tenant_id: str, user_id: str, title: str) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("title cannot be blank")
        topic = TopicTable(topic_id=_id("top"), tenant_id=tenant_id, title=title, created_by=user_id)
        conversation = ConversationTable(
            conversation_id=_id("con"), tenant_id=tenant_id, topic_id=topic.topic_id
        )
        self.repository.create_topic(topic, conversation)
        return self.topic_dict(topic, conversation_id=conversation.conversation_id)

    def get_topic(self, topic_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        topic = self.repository.get_topic(topic_id, tenant_id=tenant_id)
        if topic is None:
            return None
        conversation = self.repository.conversation_for_topic(topic_id, tenant_id=tenant_id)
        return self.topic_dict(topic, conversation_id=conversation.conversation_id if conversation else None)

    def list_topics(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [
            self.topic_dict(
                topic,
                conversation_id=(
                    conversation.conversation_id
                    if (conversation := self.repository.conversation_for_topic(topic.topic_id, tenant_id=tenant_id))
                    else None
                ),
            )
            for topic in self.repository.list_topics(tenant_id=tenant_id)
        ]

    @staticmethod
    def topic_dict(topic: TopicTable, *, conversation_id: str | None) -> dict[str, Any]:
        return {
            "topic_id": topic.topic_id,
            "tenant_id": topic.tenant_id,
            "title": topic.title,
            "conversation_id": conversation_id,
            "created_at": _iso(topic.created_at),
            "updated_at": _iso(topic.updated_at),
        }

    def create_run(
        self,
        *,
        topic_id: str,
        tenant_id: str,
        user_id: str,
        question: str,
        conversation_id: str | None = None,
        start_worker: bool | None = None,
    ) -> dict[str, Any]:
        topic = self.repository.get_topic(topic_id, tenant_id=tenant_id)
        if topic is None:
            raise KeyError(topic_id)
        question = question.strip()
        if not question:
            raise ValueError("question cannot be blank")
        if conversation_id is not None:
            conversation = self.repository.get_conversation(conversation_id, tenant_id=tenant_id)
            if conversation is None:
                raise KeyError(conversation_id)
            if conversation.topic_id != topic_id:
                raise ValueError("conversation does not belong to the requested topic")
        config = self.repository.get_active_runtime_config()
        version_id = config.version_id if config is not None else "default"
        config_snapshot = deepcopy(config.config) if config is not None else {}
        domain_pack_id = str(config_snapshot.get("domain_pack_id", "event-graph-agents-llms"))
        domain_pack = DomainPackRegistry().load(domain_pack_id)
        brief = ResearchBrief(
            brief_id=_id("brief"),
            job_id="pending",
            question=question,
            domain_pack_id=domain_pack_id,
            objectives=list(config_snapshot.get("objectives") or [question]),
            constraints={"topic_id": topic_id, "config_version_id": version_id},
        )
        dag = ResearchPlanner().plan(brief, domain_pack)
        resolved_start_worker = self._resolve_start_worker(start_worker)
        runtime_job = self.runtime_service.submit_scheduler_v2(
            brief=brief,
            dag=dag,
            config_snapshot=config_snapshot,
            max_loops=int(config_snapshot.get("max_loops", 3)),
            source_profile=config_snapshot.get("source_profile"),
            start_worker=resolved_start_worker,
            runtime_metadata={
                "product_topic_id": topic_id,
                "product_tenant_id": tenant_id,
                "product_config_version_id": version_id,
            },
        )
        runtime_status = self._status_value(runtime_job.status)
        run = RunTable(
            run_id=_id("run"),
            research_job_id=runtime_job.job_id,
            tenant_id=tenant_id,
            topic_id=topic_id,
            conversation_id=conversation_id,
            question=question,
            status=runtime_status,
            config_version_id=version_id,
            config_snapshot=config_snapshot,
            created_by=user_id,
        )
        self.repository.create_run(run)
        self.append_run_event(
            run.run_id,
            tenant_id=tenant_id,
            event_type="run.created",
            payload={
                "status": runtime_status,
                "config_version_id": version_id,
                "research_job_id": runtime_job.job_id,
            },
            dedupe_key="run.created",
        )
        self._sync_runtime_events(run)
        return self.run_dict(run)

    def _resolve_start_worker(self, requested: bool | None) -> bool:
        if not self.database.offline_mode:
            return True
        if requested is None:
            return self.start_worker_by_default
        return bool(requested)

    @staticmethod
    def _status_value(value: Any) -> str:
        return str(value.value if hasattr(value, "value") else value)

    def get_run(self, run_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        run = self.repository.get_run(run_id, tenant_id=tenant_id)
        if run is not None:
            run = self._sync_runtime_run(run)
        return self.run_dict(run) if run is not None else None

    def list_runs(self, *, tenant_id: str, topic_id: str | None = None) -> list[dict[str, Any]]:
        if topic_id is not None and self.repository.get_topic(topic_id, tenant_id=tenant_id) is None:
            raise KeyError(topic_id)
        return [
            self.run_dict(self._sync_runtime_run(run))
            for run in self.repository.list_runs(tenant_id=tenant_id, topic_id=topic_id)
        ]

    @staticmethod
    def run_dict(run: RunTable) -> dict[str, Any]:
        return {
            "run_id": run.run_id,
            "research_job_id": run.research_job_id,
            "tenant_id": run.tenant_id,
            "topic_id": run.topic_id,
            "conversation_id": run.conversation_id,
            "question": run.question,
            "status": run.status,
            "config_version_id": run.config_version_id,
            "snapshot_cutoff": run.snapshot_cutoff,
            "cancel_requested": run.cancel_requested,
            "created_at": _iso(run.created_at),
            "updated_at": _iso(run.updated_at),
        }

    def append_run_event(
        self,
        run_id: str,
        *,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        dedupe_key: str | None = None,
    ) -> dict[str, Any]:
        resolved_key = dedupe_key or f"{event_type}:{secrets.token_hex(12)}"
        event = self.repository.append_event(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            dedupe_key=resolved_key,
        )
        return self.event_dict(event)

    def list_run_events(
        self, run_id: str, *, tenant_id: str, after_sequence: int = 0
    ) -> list[dict[str, Any]] | None:
        run = self.repository.get_run(run_id, tenant_id=tenant_id)
        if run is None:
            return None
        self._sync_runtime_run(run)
        events = self.repository.list_events(
            run_id, tenant_id=tenant_id, after_sequence=after_sequence
        )
        return None if events is None else [self.event_dict(event) for event in events]

    @staticmethod
    def event_dict(event: RunEventTable) -> dict[str, Any]:
        return {
            "event_id": str(event.sequence),
            "run_id": event.run_id,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "payload": deepcopy(event.payload),
            "created_at": _iso(event.created_at),
        }

    def cancel_run(self, run_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        run = self.repository.get_run(run_id, tenant_id=tenant_id)
        if run is None:
            return None
        self.runtime_service.cancel(run.research_job_id)
        return self.run_dict(self._sync_runtime_run(run, allow_terminal_downgrade=True))

    def resume_run(
        self,
        run_id: str,
        *,
        tenant_id: str,
        start_worker: bool | None = None,
    ) -> dict[str, Any] | None:
        run = self.repository.get_run(run_id, tenant_id=tenant_id)
        if run is None:
            return None
        run = self._sync_runtime_run(run)
        if run.status not in {"cancelled", "failed"}:
            raise ValueError(f"cannot resume a {run.status} run")
        self.runtime_service.resume(
            run.research_job_id,
            start_worker=self._resolve_start_worker(start_worker),
        )
        return self.run_dict(self._sync_runtime_run(run, allow_terminal_downgrade=True))

    def complete_run(
        self,
        run_id: str,
        *,
        tenant_id: str,
        bundle: dict[str, Any],
        snapshot_cutoff: str,
    ) -> dict[str, Any]:
        updated = self.repository.update_run(
            run_id,
            tenant_id=tenant_id,
            status="completed",
            bundle=deepcopy(bundle),
            snapshot_cutoff=snapshot_cutoff,
        )
        if updated is None:
            raise KeyError(run_id)
        self.append_run_event(
            run_id,
            tenant_id=tenant_id,
            event_type="run.completed",
            payload={"terminal": True, "status": "completed", "snapshot_cutoff": snapshot_cutoff},
            dedupe_key="run.completed",
        )
        return self.run_dict(updated)

    def get_bundle(self, run_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        run = self.repository.get_run(run_id, tenant_id=tenant_id)
        if run is None:
            raise KeyError(run_id)
        run = self._sync_runtime_run(run)
        return deepcopy(run.bundle)

    def _sync_runtime_run(
        self,
        run: RunTable,
        *,
        allow_terminal_downgrade: bool = False,
    ) -> RunTable:
        runtime_job = self.runtime_service.get(run.research_job_id)
        if runtime_job is None:
            return run
        runtime_status = self._status_value(runtime_job.status)
        if (
            not allow_terminal_downgrade
            and run.status in TERMINAL_RUN_STATUSES
            and runtime_status not in TERMINAL_RUN_STATUSES
        ):
            return run

        runtime_event_types = self._sync_runtime_events(run)
        updates: dict[str, Any] = {
            "status": runtime_status,
            "cancel_requested": bool(runtime_job.cancel_requested),
        }
        bundle_path = Path(runtime_job.report_bundle_path)
        if runtime_status == "completed" and bundle_path.is_file():
            updates["bundle"] = json.loads(bundle_path.read_text(encoding="utf-8"))
            updates["snapshot_cutoff"] = runtime_job.updated_at
        status_changed = run.status != runtime_status
        updated = self.repository.update_run(
            run.run_id,
            tenant_id=run.tenant_id,
            **updates,
        )
        if updated is None:
            return run
        matching_runtime_events = {
            "cancelled": "job.cancelled",
            "completed": "job.completed",
            "created": "job.resumed",
            "failed": "job.failed",
        }
        if status_changed and matching_runtime_events.get(runtime_status) not in runtime_event_types:
            terminal = runtime_status in TERMINAL_RUN_STATUSES
            self.append_run_event(
                run.run_id,
                tenant_id=run.tenant_id,
                event_type=f"run.{runtime_status}",
                payload={"status": runtime_status, "terminal": terminal},
                dedupe_key=f"runtime-status:{runtime_status}:{runtime_job.updated_at}",
            )
        return updated

    def _sync_runtime_events(self, run: RunTable) -> set[str]:
        event_types: set[str] = set()
        for event in self.runtime_service.list_events(run.research_job_id, after_sequence=0):
            event_types.add(event.event_type)
            if event.event_type == "job.created":
                continue
            event_type = event.event_type
            if event_type.startswith("job."):
                event_type = f"run.{event_type.removeprefix('job.')}"
            else:
                event_type = f"runtime.{event_type}"
            terminal = event.event_type in {"job.completed", "job.failed", "job.cancelled"}
            payload = dict(event.payload)
            payload.update(
                {
                    "runtime_event_id": event.event_id,
                    "runtime_sequence": event.sequence,
                    "stage": event.stage,
                    "message": event.message,
                    "terminal": terminal,
                }
            )
            self.append_run_event(
                run.run_id,
                tenant_id=run.tenant_id,
                event_type=event_type,
                payload=payload,
                dedupe_key=f"runtime-event:{event.event_id}",
            )
        return event_types

    def respond_to_message(
        self,
        conversation_id: str,
        *,
        tenant_id: str,
        user_id: str,
        content: str,
        refresh: bool,
    ) -> dict[str, Any]:
        conversation = self.repository.get_conversation(conversation_id, tenant_id=tenant_id)
        if conversation is None:
            raise KeyError(conversation_id)
        content = content.strip()
        if not content:
            raise ValueError("content cannot be blank")
        self.repository.add_message(
            MessageTable(
                message_id=_id("msg"),
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role="user",
                content=content,
            )
        )
        for candidate in self.repository.list_runs(tenant_id=tenant_id, topic_id=conversation.topic_id):
            self._sync_runtime_run(candidate)
        latest = self.repository.latest_completed_run(conversation.topic_id, tenant_id=tenant_id)
        topic = self.repository.get_topic(conversation.topic_id, tenant_id=tenant_id)
        words = content.casefold().split()
        high_cost = any(marker in content.casefold() for marker in _HIGH_COST_MARKERS)
        ambiguous = len(words) <= 2 or content.casefold() in {"research it", "look into it", "compare them"}
        run: dict[str, Any] | None = None
        answer: str | None = None
        questions: list[str] = []
        used_snapshot = False
        if refresh:
            response_type = "research_job_started"
            run = self.create_run(
                topic_id=conversation.topic_id,
                tenant_id=tenant_id,
                user_id=user_id,
                question=content,
                conversation_id=conversation_id,
            )
        elif high_cost or ambiguous:
            response_type = "clarification_required"
            questions = [
                "What decision should this research support?",
                "Which scope and evidence cutoff should be used?",
            ]
        elif self._is_simple_question(content):
            response_type = "direct_answer"
            answer = self._direct_answer(content)
        elif latest is not None and self._is_relevant_follow_up(
            content,
            topic_title=topic.title if topic is not None else "",
            prior_question=latest.question,
        ):
            response_type = "direct_answer"
            answer = str((latest.bundle or {}).get("report_markdown") or "The frozen snapshot has no report text.")
            used_snapshot = True
        else:
            response_type = "research_job_started"
            run = self.create_run(
                topic_id=conversation.topic_id,
                tenant_id=tenant_id,
                user_id=user_id,
                question=content,
                conversation_id=conversation_id,
            )
        brief = {
            "brief_id": _id("brf"),
            "run_id": run["run_id"] if run else None,
            "question": content,
            "objectives": [content] if response_type != "clarification_required" else [],
            "constraints": {"refresh": refresh, "high_cost": high_cost},
            "snapshot_cutoff": latest.snapshot_cutoff if used_snapshot else None,
        }
        self.repository.add_message(
            MessageTable(
                message_id=_id("msg"),
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role="assistant",
                content=answer or "\n".join(questions) or "Research run started.",
                response_type=response_type,
            )
        )
        return {
            "response_type": response_type,
            "brief": brief,
            "answer": answer,
            "clarification_questions": questions,
            "run_id": run["run_id"] if run else None,
        }

    @staticmethod
    def _is_simple_question(content: str) -> bool:
        lowered = content.casefold()
        return bool(re.fullmatch(r"what is\s+\d+\s*\+\s*\d+\??", lowered)) or (
            len(content.split()) <= 12
            and lowered.startswith(("what is ", "who is ", "define ", "hello", "hi "))
        )

    @staticmethod
    def _direct_answer(content: str) -> str:
        match = re.fullmatch(r"what is\s+(\d+)\s*\+\s*(\d+)\??", content.casefold())
        if match:
            return str(int(match.group(1)) + int(match.group(2)))
        return "This question can be answered directly without starting a research run."

    @staticmethod
    def _is_relevant_follow_up(content: str, *, topic_title: str, prior_question: str) -> bool:
        def terms(value: str) -> set[str]:
            return {
                token
                for token in re.findall(r"[a-z0-9]+", value.casefold())
                if len(token) > 2 and token not in _FOLLOW_UP_STOP_WORDS
            }

        return bool(terms(content) & terms(f"{topic_title} {prior_question}"))

    def upload_corpus(
        self,
        *,
        tenant_id: str,
        user_id: str,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        if not content:
            raise ValueError("uploaded file cannot be empty")
        document = CorpusDocumentTable(
            document_id=_id("doc"),
            tenant_id=tenant_id,
            filename=filename or "upload.bin",
            media_type=media_type or "application/octet-stream",
            content_sha256=hashlib.sha256(content).hexdigest(),
            content=content,
            uploaded_by=user_id,
        )
        self.repository.create_corpus_document(document)
        return self.corpus_dict(document)

    def get_corpus(self, document_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        document = self.repository.get_corpus_document(document_id, tenant_id=tenant_id)
        return self.corpus_dict(document) if document is not None else None

    def list_corpus(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [self.corpus_dict(item) for item in self.repository.list_corpus_documents(tenant_id=tenant_id)]

    @staticmethod
    def corpus_dict(document: CorpusDocumentTable) -> dict[str, Any]:
        return {
            "document_id": document.document_id,
            "tenant_id": document.tenant_id,
            "filename": document.filename,
            "media_type": document.media_type,
            "content_sha256": document.content_sha256,
            "visibility": "private",
            "created_at": _iso(document.created_at),
        }

    def create_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        scope: str,
        content: str,
        confidence: float,
    ) -> dict[str, Any]:
        if scope not in MEMORY_SCOPES:
            raise ValueError(f"unsupported memory scope: {scope}")
        memory = MemoryTable(
            memory_id=_id("mem"),
            tenant_id=tenant_id,
            user_id=user_id,
            scope=scope,
            content=content.strip(),
            confidence=confidence,
        )
        if not memory.content:
            raise ValueError("memory content cannot be blank")
        self.repository.create_memory(memory)
        return self.memory_dict(memory)

    def get_memory(self, memory_id: str, *, tenant_id: str, user_id: str) -> dict[str, Any] | None:
        memory = self.repository.get_memory(memory_id, tenant_id=tenant_id, user_id=user_id)
        return self.memory_dict(memory) if memory is not None else None

    def list_memories(self, *, tenant_id: str, user_id: str) -> list[dict[str, Any]]:
        return [
            self.memory_dict(memory)
            for memory in self.repository.list_memories(tenant_id=tenant_id, user_id=user_id)
        ]

    def update_memory(
        self,
        memory_id: str,
        *,
        tenant_id: str,
        user_id: str,
        content: str | None,
        confidence: float | None,
    ) -> dict[str, Any] | None:
        values: dict[str, Any] = {}
        if content is not None:
            if not content.strip():
                raise ValueError("memory content cannot be blank")
            values["content"] = content.strip()
        if confidence is not None:
            values["confidence"] = confidence
        memory = self.repository.update_memory(
            memory_id, tenant_id=tenant_id, user_id=user_id, values=values
        )
        return self.memory_dict(memory) if memory is not None else None

    @staticmethod
    def memory_dict(memory: MemoryTable) -> dict[str, Any]:
        return {
            "memory_id": memory.memory_id,
            "tenant_id": memory.tenant_id,
            "user_id": memory.user_id,
            "scope": memory.scope,
            "content": memory.content,
            "confidence": memory.confidence,
            "status": memory.status,
            "created_at": _iso(memory.created_at),
            "updated_at": _iso(memory.updated_at),
        }

    def create_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = str(payload["api_key"])
        model = ModelEndpointTable(
            endpoint_id=str(payload["endpoint_id"]),
            base_url=str(payload["base_url"]),
            model=str(payload["model"]),
            secret_digest=hashlib.sha256(api_key.encode()).hexdigest(),
            enabled=bool(payload.get("enabled", True)),
        )
        self.repository.save_model(model)
        return self.model_dict(model)

    @staticmethod
    def model_dict(model: ModelEndpointTable) -> dict[str, Any]:
        return {
            "endpoint_id": model.endpoint_id,
            "base_url": model.base_url,
            "model": model.model,
            "api_key": "[redacted]",
            "enabled": model.enabled,
        }

    def create_tool(self, *, tool_id: str, config: dict[str, Any], enabled: bool) -> dict[str, Any]:
        tool = self.repository.save_tool(
            ToolConfigTable(tool_id=tool_id, config=deepcopy(config), enabled=enabled)
        )
        return self.tool_dict(tool)

    @staticmethod
    def tool_dict(tool: ToolConfigTable) -> dict[str, Any]:
        return {"tool_id": tool.tool_id, "config": redact_secrets(tool.config), "enabled": tool.enabled}

    def create_runtime_config(self, *, version_id: str, config: dict[str, Any]) -> dict[str, Any]:
        if _contains_secret_key(config):
            raise ValueError("runtime config must reference stored credentials, not contain secrets")
        record = self.repository.save_runtime_config(
            RuntimeConfigTable(version_id=version_id, config=deepcopy(config), active=False)
        )
        return self.runtime_config_dict(record)

    @staticmethod
    def runtime_config_dict(config: RuntimeConfigTable) -> dict[str, Any]:
        return {
            "version_id": config.version_id,
            "config": redact_secrets(deepcopy(config.config)),
            "active": config.active,
            "created_at": _iso(config.created_at),
        }


__all__ = ["MEMORY_SCOPES", "ProductService", "TERMINAL_RUN_STATUSES", "redact_secrets"]
