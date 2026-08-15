"""Tenant-scoped SQL repositories for product state."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from deep_research_agent.product.tables import (
    ConversationTable,
    CorpusDocumentTable,
    InvitationTable,
    MemoryTable,
    MessageTable,
    ModelEndpointTable,
    RunEventTable,
    RunTable,
    RuntimeConfigTable,
    SessionTable,
    ToolConfigTable,
    TopicTable,
    UserTable,
    utc_now,
)


class ProductRepository:
    """Persistence facade whose workspace reads always require a tenant ID."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with self.sessions() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def user_count(self) -> int:
        with self.sessions() as session:
            return int(session.scalar(select(func.count()).select_from(UserTable)) or 0)

    def create_user(self, user: UserTable) -> UserTable:
        with self._session() as session:
            session.add(user)
            try:
                session.commit()
            except IntegrityError as exc:
                # 并发注册/邀请接受时 check-then-create 不是原子的，第二个写入
                # 会撞唯一约束；转成确定性错误而不是 500。
                session.rollback()
                raise ValueError("email already registered") from exc
        return user

    def get_user_by_email(self, email: str) -> UserTable | None:
        with self.sessions() as session:
            return session.scalar(select(UserTable).where(UserTable.email == email.casefold()))

    def get_user(self, user_id: str) -> UserTable | None:
        with self.sessions() as session:
            return session.get(UserTable, user_id)

    def create_invitation(self, invitation: InvitationTable) -> InvitationTable:
        with self._session() as session:
            session.add(invitation)
        return invitation

    def get_invitation_by_token_hash(self, token_hash: str) -> InvitationTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(InvitationTable).where(InvitationTable.token_hash == token_hash)
            )

    def accept_invitation(self, invitation_id: str, accepted_at: datetime) -> None:
        with self._session() as session:
            invitation = session.get(InvitationTable, invitation_id)
            if invitation is None:
                raise KeyError(invitation_id)
            invitation.accepted_at = accepted_at

    def create_session(self, record: SessionTable) -> SessionTable:
        with self._session() as session:
            session.add(record)
        return record

    def get_session_by_token_hash(self, token_hash: str) -> SessionTable | None:
        with self.sessions() as session:
            return session.scalar(select(SessionTable).where(SessionTable.token_hash == token_hash))

    def delete_session_by_token_hash(self, token_hash: str) -> None:
        with self._session() as session:
            record = session.scalar(
                select(SessionTable).where(SessionTable.token_hash == token_hash)
            )
            if record is not None:
                session.delete(record)

    def create_topic(self, topic: TopicTable, conversation: ConversationTable) -> TopicTable:
        with self._session() as session:
            session.add(topic)
            session.flush()
            session.add(conversation)
        return topic

    def get_topic(self, topic_id: str, *, tenant_id: str) -> TopicTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(TopicTable).where(
                    TopicTable.topic_id == topic_id,
                    TopicTable.tenant_id == tenant_id,
                )
            )

    def list_topics(self, *, tenant_id: str) -> list[TopicTable]:
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(TopicTable)
                    .where(TopicTable.tenant_id == tenant_id)
                    .order_by(TopicTable.updated_at.desc(), TopicTable.topic_id)
                )
            )

    def get_conversation(self, conversation_id: str, *, tenant_id: str) -> ConversationTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(ConversationTable).where(
                    ConversationTable.conversation_id == conversation_id,
                    ConversationTable.tenant_id == tenant_id,
                )
            )

    def conversation_for_topic(self, topic_id: str, *, tenant_id: str) -> ConversationTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(ConversationTable).where(
                    ConversationTable.topic_id == topic_id,
                    ConversationTable.tenant_id == tenant_id,
                )
            )

    def add_message(self, message: MessageTable) -> MessageTable:
        with self._session() as session:
            session.add(message)
        return message

    def create_run(self, run: RunTable) -> RunTable:
        with self._session() as session:
            session.add(run)
        return run

    def get_run(self, run_id: str, *, tenant_id: str) -> RunTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(RunTable).where(RunTable.run_id == run_id, RunTable.tenant_id == tenant_id)
            )

    def list_runs(self, *, tenant_id: str, topic_id: str | None = None) -> list[RunTable]:
        statement = select(RunTable).where(RunTable.tenant_id == tenant_id)
        if topic_id is not None:
            statement = statement.where(RunTable.topic_id == topic_id)
        with self.sessions() as session:
            return list(
                session.scalars(statement.order_by(RunTable.created_at.desc(), RunTable.run_id))
            )

    def latest_completed_run(self, topic_id: str, *, tenant_id: str) -> RunTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(RunTable)
                .where(
                    RunTable.topic_id == topic_id,
                    RunTable.tenant_id == tenant_id,
                    RunTable.status == "completed",
                    RunTable.bundle.is_not(None),
                )
                .order_by(RunTable.updated_at.desc())
                .limit(1)
            )

    def update_run(self, run_id: str, *, tenant_id: str, **values: Any) -> RunTable | None:
        with self._session() as session:
            run = session.scalar(
                select(RunTable).where(RunTable.run_id == run_id, RunTable.tenant_id == tenant_id)
            )
            if run is None:
                return None
            for name, value in values.items():
                setattr(run, name, value)
            run.updated_at = utc_now()
        return run

    def append_event(
        self,
        *,
        run_id: str,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        dedupe_key: str,
    ) -> RunEventTable:
        for _ in range(5):
            try:
                with self._session() as session:
                    run = session.scalar(
                        select(RunTable)
                        .where(RunTable.run_id == run_id, RunTable.tenant_id == tenant_id)
                        .with_for_update()
                    )
                    if run is None:
                        raise KeyError(run_id)
                    existing = session.scalar(
                        select(RunEventTable).where(
                            RunEventTable.run_id == run_id,
                            RunEventTable.dedupe_key == dedupe_key,
                        )
                    )
                    if existing is not None:
                        return existing
                    last_sequence = session.scalar(
                        select(func.max(RunEventTable.sequence)).where(
                            RunEventTable.run_id == run_id
                        )
                    )
                    event = RunEventTable(
                        run_id=run_id,
                        tenant_id=tenant_id,
                        sequence=int(last_sequence or 0) + 1,
                        event_type=event_type,
                        dedupe_key=dedupe_key,
                        payload=dict(payload),
                    )
                    session.add(event)
                return event
            except IntegrityError:
                with self.sessions() as session:
                    existing = session.scalar(
                        select(RunEventTable).where(
                            RunEventTable.run_id == run_id,
                            RunEventTable.dedupe_key == dedupe_key,
                        )
                    )
                    if existing is not None:
                        return existing
        raise RuntimeError(f"could not append event after concurrent updates: {dedupe_key}")

    def list_events(
        self, run_id: str, *, tenant_id: str, after_sequence: int = 0
    ) -> list[RunEventTable] | None:
        if self.get_run(run_id, tenant_id=tenant_id) is None:
            return None
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(RunEventTable)
                    .where(
                        RunEventTable.run_id == run_id,
                        RunEventTable.tenant_id == tenant_id,
                        RunEventTable.sequence > after_sequence,
                    )
                    .order_by(RunEventTable.sequence)
                )
            )

    def create_corpus_document(self, document: CorpusDocumentTable) -> CorpusDocumentTable:
        with self._session() as session:
            session.add(document)
        return document

    def get_corpus_document(
        self, document_id: str, *, tenant_id: str
    ) -> CorpusDocumentTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(CorpusDocumentTable).where(
                    CorpusDocumentTable.document_id == document_id,
                    CorpusDocumentTable.tenant_id == tenant_id,
                )
            )

    def list_corpus_documents(self, *, tenant_id: str) -> list[CorpusDocumentTable]:
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(CorpusDocumentTable)
                    .where(CorpusDocumentTable.tenant_id == tenant_id)
                    .order_by(CorpusDocumentTable.created_at.desc())
                )
            )

    def create_memory(self, memory: MemoryTable) -> MemoryTable:
        with self._session() as session:
            session.add(memory)
        return memory

    def get_memory(self, memory_id: str, *, tenant_id: str, user_id: str) -> MemoryTable | None:
        with self.sessions() as session:
            memory = session.scalar(
                select(MemoryTable).where(
                    MemoryTable.memory_id == memory_id,
                    MemoryTable.tenant_id == tenant_id,
                    MemoryTable.user_id == user_id,
                )
            )
            if memory is not None and memory.expires_at is not None:
                now = utc_now()
                expires_at = memory.expires_at
                if expires_at.tzinfo is None:
                    now = now.replace(tzinfo=None)
                if expires_at <= now:
                    return None
            return memory

    def list_memories(
        self,
        *,
        tenant_id: str,
        user_id: str,
        scopes_and_subjects: list[tuple[str, str | None]] | None = None,
    ) -> list[MemoryTable]:
        with self._session() as session:
            statement = select(MemoryTable).where(
                MemoryTable.tenant_id == tenant_id,
                MemoryTable.user_id == user_id,
                MemoryTable.status == "active",
            )
            if scopes_and_subjects is not None:
                from sqlalchemy import or_

                statement = statement.where(
                    or_(
                        *(
                            (MemoryTable.scope == scope) & (MemoryTable.subject_id == subject_id)
                            for scope, subject_id in scopes_and_subjects
                        )
                    )
                )
            memories = list(
                session.scalars(statement.order_by(MemoryTable.created_at, MemoryTable.memory_id))
            )
            now = utc_now()
            active: list[MemoryTable] = []
            for memory in memories:
                if memory.expires_at is not None:
                    expires_at = memory.expires_at
                    comparison_now = now.replace(tzinfo=None) if expires_at.tzinfo is None else now
                    if expires_at <= comparison_now:
                        memory.status = "expired"
                        memory.updated_at = now
                        continue
                active.append(memory)
            return active

    def supersede_memory_key(
        self, *, tenant_id: str, user_id: str, subject_id: str | None, key: str
    ) -> MemoryTable | None:
        with self._session() as session:
            memory = session.scalar(
                select(MemoryTable)
                .where(
                    MemoryTable.tenant_id == tenant_id,
                    MemoryTable.user_id == user_id,
                    MemoryTable.subject_id == subject_id,
                    MemoryTable.key == key,
                    MemoryTable.status == "active",
                )
                .order_by(MemoryTable.updated_at.desc())
            )
            if memory is None:
                return None
            memory.status = "superseded"
            memory.updated_at = utc_now()
            return memory

    def update_memory(
        self, memory_id: str, *, tenant_id: str, user_id: str, values: dict[str, Any]
    ) -> MemoryTable | None:
        with self._session() as session:
            memory = session.scalar(
                select(MemoryTable).where(
                    MemoryTable.memory_id == memory_id,
                    MemoryTable.tenant_id == tenant_id,
                    MemoryTable.user_id == user_id,
                )
            )
            if memory is None:
                return None
            for name, value in values.items():
                setattr(memory, name, value)
            memory.updated_at = utc_now()
        return memory

    def delete_memory(self, memory_id: str, *, tenant_id: str, user_id: str) -> bool:
        with self._session() as session:
            memory = session.scalar(
                select(MemoryTable).where(
                    MemoryTable.memory_id == memory_id,
                    MemoryTable.tenant_id == tenant_id,
                    MemoryTable.user_id == user_id,
                )
            )
            if memory is None:
                return False
            session.delete(memory)
        return True

    def save_model(self, model: ModelEndpointTable) -> ModelEndpointTable:
        with self._session() as session:
            if session.get(ModelEndpointTable, model.endpoint_id) is not None:
                raise ValueError(f"model endpoint {model.endpoint_id!r} already exists")
            session.add(model)
        return model

    def list_models(self) -> list[ModelEndpointTable]:
        with self.sessions() as session:
            return list(
                session.scalars(select(ModelEndpointTable).order_by(ModelEndpointTable.endpoint_id))
            )

    def save_tool(self, tool: ToolConfigTable) -> ToolConfigTable:
        with self._session() as session:
            existing = session.get(ToolConfigTable, tool.tool_id)
            if existing is None:
                session.add(tool)
                return tool
            existing.config = tool.config
            existing.enabled = tool.enabled
            return existing

    def list_tools(self) -> list[ToolConfigTable]:
        with self.sessions() as session:
            return list(session.scalars(select(ToolConfigTable).order_by(ToolConfigTable.tool_id)))

    def save_runtime_config(self, config: RuntimeConfigTable) -> RuntimeConfigTable:
        with self._session() as session:
            if session.get(RuntimeConfigTable, config.version_id) is not None:
                raise ValueError(f"runtime config {config.version_id!r} already exists")
            session.add(config)
        return config

    def activate_runtime_config(self, version_id: str) -> RuntimeConfigTable:
        with self._session() as session:
            config = session.get(RuntimeConfigTable, version_id)
            if config is None:
                raise KeyError(version_id)
            session.execute(update(RuntimeConfigTable).values(active=False))
            config.active = True
        return config

    def get_active_runtime_config(self) -> RuntimeConfigTable | None:
        with self.sessions() as session:
            return session.scalar(
                select(RuntimeConfigTable).where(RuntimeConfigTable.active.is_(True))
            )

    def list_runtime_configs(self) -> list[RuntimeConfigTable]:
        with self.sessions() as session:
            return list(
                session.scalars(select(RuntimeConfigTable).order_by(RuntimeConfigTable.created_at))
            )


__all__ = ["ProductRepository"]
