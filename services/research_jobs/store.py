"""Phase 02 research job 的 SQLite 存储。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from artifacts.schemas import validate_instance
from services.research_jobs.models import (
    ACTIVE_JOB_STATUSES,
    JobCheckpoint,
    JobProgressEvent,
    JobRuntimeRecord,
    utc_now_iso,
)


class ResearchJobStore:
    """负责 research job runtime record、event 与 checkpoint 的持久化。"""

    def __init__(self, workspace_dir: str = "workspace", runtime_dirname: str = "research_jobs") -> None:
        self.workspace_root = Path(workspace_dir)
        self.root = self.workspace_root / runtime_dirname
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "jobs.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    attempt_index INTEGER NOT NULL,
                    retry_of TEXT,
                    cancel_requested INTEGER NOT NULL,
                    worker_pid INTEGER,
                    worker_lease_id TEXT,
                    last_heartbeat_at TEXT,
                    active_checkpoint_id TEXT,
                    report_path TEXT NOT NULL,
                    report_bundle_path TEXT NOT NULL,
                    trace_path TEXT NOT NULL,
                    runtime_path TEXT NOT NULL,
                    source_profile TEXT NOT NULL DEFAULT 'open-web',
                    budget_json TEXT NOT NULL DEFAULT '{}',
                    policy_overrides_json TEXT NOT NULL DEFAULT '{}',
                    connector_health_json TEXT NOT NULL DEFAULT '{}',
                    audit_gate_status TEXT NOT NULL DEFAULT 'unchecked',
                    critical_claim_count INTEGER NOT NULL DEFAULT 0,
                    blocked_critical_claim_count INTEGER NOT NULL DEFAULT 0,
                    audit_graph_path TEXT NOT NULL DEFAULT '',
                    review_queue_path TEXT NOT NULL DEFAULT '',
                    error TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_events (
                    job_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (job_id, sequence)
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "source_profile" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN source_profile TEXT NOT NULL DEFAULT 'open-web'")
            if "budget_json" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN budget_json TEXT NOT NULL DEFAULT '{}'")
            if "policy_overrides_json" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN policy_overrides_json TEXT NOT NULL DEFAULT '{}'")
            if "connector_health_json" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN connector_health_json TEXT NOT NULL DEFAULT '{}'")
            if "audit_gate_status" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN audit_gate_status TEXT NOT NULL DEFAULT 'unchecked'")
            if "critical_claim_count" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN critical_claim_count INTEGER NOT NULL DEFAULT 0")
            if "blocked_critical_claim_count" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN blocked_critical_claim_count INTEGER NOT NULL DEFAULT 0")
            if "audit_graph_path" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN audit_graph_path TEXT NOT NULL DEFAULT ''")
            if "review_queue_path" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN review_queue_path TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_checkpoints (
                    job_id TEXT NOT NULL,
                    checkpoint_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    loop_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    next_stage TEXT NOT NULL,
                    payload_ref TEXT NOT NULL
                )
                """
            )

    def job_dir(self, job_id: str) -> Path:
        path = self.root / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def checkpoint_dir(self, job_id: str) -> Path:
        path = self.job_dir(job_id) / "checkpoints"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def bundle_dir(self, job_id: str) -> Path:
        path = self.job_dir(job_id) / "bundle"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upsert_job(self, job: JobRuntimeRecord) -> JobRuntimeRecord:
        payload = job.model_dump(mode="json")
        validate_instance("job-runtime-record", payload)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs (
                    job_id, topic, status, current_stage, created_at, updated_at,
                    attempt_index, retry_of, cancel_requested, worker_pid, worker_lease_id,
                    last_heartbeat_at, active_checkpoint_id, report_path, report_bundle_path,
                    trace_path, runtime_path, source_profile, budget_json, policy_overrides_json,
                    connector_health_json, audit_gate_status, critical_claim_count,
                    blocked_critical_claim_count, audit_graph_path, review_queue_path,
                    error, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["job_id"],
                    payload["topic"],
                    payload["status"],
                    payload["current_stage"],
                    payload["created_at"],
                    payload["updated_at"],
                    payload["attempt_index"],
                    payload.get("retry_of"),
                    int(payload["cancel_requested"]),
                    payload.get("worker_pid"),
                    payload.get("worker_lease_id"),
                    payload.get("last_heartbeat_at"),
                    payload.get("active_checkpoint_id"),
                    payload["report_path"],
                    payload["report_bundle_path"],
                    payload["trace_path"],
                    payload["runtime_path"],
                    payload["source_profile"],
                    json.dumps(payload.get("budget") or {}, ensure_ascii=False),
                    json.dumps(payload.get("policy_overrides") or {}, ensure_ascii=False),
                    json.dumps(payload.get("connector_health") or {}, ensure_ascii=False),
                    payload.get("audit_gate_status", "unchecked"),
                    int(payload.get("critical_claim_count", 0)),
                    int(payload.get("blocked_critical_claim_count", 0)),
                    payload.get("audit_graph_path", ""),
                    payload.get("review_queue_path", ""),
                    payload.get("error"),
                    json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
                ),
            )
        return job

    def get_job(self, job_id: str) -> JobRuntimeRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def list_active_jobs(self) -> list[JobRuntimeRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs").fetchall()
        jobs = [self._row_to_job(row) for row in rows]
        return [job for job in jobs if job.status in ACTIVE_JOB_STATUSES]

    def update_job(self, job_id: str, **fields) -> JobRuntimeRecord:
        current = self.get_job(job_id)
        if current is None:
            raise KeyError(f"未知 job: {job_id}")
        payload = current.model_dump(mode="json")
        payload.update(fields)
        payload["updated_at"] = utc_now_iso()
        job = JobRuntimeRecord.model_validate(payload)
        return self.upsert_job(job)

    def update_job_status(
        self,
        job_id: str,
        *,
        status: str,
        current_stage: str | None = None,
        error: str | None = None,
        cancel_requested: bool | None = None,
        active_checkpoint_id: str | None = None,
    ) -> JobRuntimeRecord:
        updates = {"status": status}
        if current_stage is not None:
            updates["current_stage"] = current_stage
        if error is not None:
            updates["error"] = error
        if cancel_requested is not None:
            updates["cancel_requested"] = cancel_requested
        if active_checkpoint_id is not None:
            updates["active_checkpoint_id"] = active_checkpoint_id
        return self.update_job(job_id, **updates)

    def attach_worker(self, job_id: str, *, worker_pid: int, lease_id: str) -> JobRuntimeRecord:
        return self.update_job(
            job_id,
            worker_pid=worker_pid,
            worker_lease_id=lease_id,
            last_heartbeat_at=utc_now_iso(),
        )

    def clear_worker(self, job_id: str) -> JobRuntimeRecord:
        return self.update_job(job_id, worker_pid=None, worker_lease_id=None)

    def heartbeat(self, job_id: str, *, lease_id: str | None = None) -> JobRuntimeRecord:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"未知 job: {job_id}")
        if lease_id is not None and job.worker_lease_id != lease_id:
            return job
        return self.update_job(job_id, last_heartbeat_at=utc_now_iso())

    def next_event_sequence(self, job_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM job_events WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return int(row["max_sequence"]) + 1 if row is not None else 1

    def append_event(self, event: JobProgressEvent) -> JobProgressEvent:
        payload = event.model_dump(mode="json")
        validate_instance("job-progress-event", payload)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_events (
                    job_id, sequence, event_id, stage, event_type, timestamp, message, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["job_id"],
                    payload["sequence"],
                    payload["event_id"],
                    payload["stage"],
                    payload["event_type"],
                    payload["timestamp"],
                    payload["message"],
                    json.dumps(payload.get("payload") or {}, ensure_ascii=False),
                ),
            )
        return event

    def list_events(self, job_id: str, *, after_sequence: int = 0) -> list[JobProgressEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_events
                WHERE job_id = ? AND sequence > ?
                ORDER BY sequence ASC
                """,
                (job_id, after_sequence),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def next_checkpoint_sequence(self, job_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM job_checkpoints WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return int(row["max_sequence"]) + 1 if row is not None else 1

    def save_checkpoint(self, checkpoint: JobCheckpoint) -> JobCheckpoint:
        payload = checkpoint.model_dump(mode="json")
        validate_instance("job-checkpoint", payload)
        checkpoint_path = self.checkpoint_dir(checkpoint.job_id) / f"{checkpoint.sequence:04d}-{checkpoint.stage}.json"
        checkpoint_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_checkpoints (
                    job_id, checkpoint_id, sequence, stage, loop_count, created_at, next_stage, payload_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.job_id,
                    checkpoint.checkpoint_id,
                    checkpoint.sequence,
                    checkpoint.stage,
                    checkpoint.loop_count,
                    checkpoint.created_at,
                    checkpoint.next_stage,
                    str(checkpoint_path),
                ),
            )
        return checkpoint

    def get_checkpoint(self, job_id: str, checkpoint_id: str) -> JobCheckpoint | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM job_checkpoints WHERE job_id = ? AND checkpoint_id = ?",
                (job_id, checkpoint_id),
            ).fetchone()
        if row is None:
            return None
        return self._read_checkpoint_row(row)

    def get_latest_checkpoint(self, job_id: str) -> JobCheckpoint | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM job_checkpoints
                WHERE job_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return self._read_checkpoint_row(row)

    def _row_to_job(self, row: sqlite3.Row) -> JobRuntimeRecord:
        return JobRuntimeRecord.model_validate(
            {
                "job_id": row["job_id"],
                "topic": row["topic"],
                "status": row["status"],
                "current_stage": row["current_stage"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "attempt_index": row["attempt_index"],
                "retry_of": row["retry_of"],
                "cancel_requested": bool(row["cancel_requested"]),
                "worker_pid": row["worker_pid"],
                "worker_lease_id": row["worker_lease_id"],
                "last_heartbeat_at": row["last_heartbeat_at"],
                "active_checkpoint_id": row["active_checkpoint_id"],
                "report_path": row["report_path"],
                "report_bundle_path": row["report_bundle_path"],
                "trace_path": row["trace_path"],
                "runtime_path": row["runtime_path"],
                "source_profile": row["source_profile"],
                "budget": json.loads(row["budget_json"] or "{}"),
                "policy_overrides": json.loads(row["policy_overrides_json"] or "{}"),
                "connector_health": json.loads(row["connector_health_json"] or "{}"),
                "audit_gate_status": row["audit_gate_status"],
                "critical_claim_count": row["critical_claim_count"],
                "blocked_critical_claim_count": row["blocked_critical_claim_count"],
                "audit_graph_path": row["audit_graph_path"],
                "review_queue_path": row["review_queue_path"],
                "error": row["error"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
        )

    def _row_to_event(self, row: sqlite3.Row) -> JobProgressEvent:
        return JobProgressEvent.model_validate(
            {
                "event_id": row["event_id"],
                "job_id": row["job_id"],
                "sequence": row["sequence"],
                "stage": row["stage"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"] or "{}"),
            }
        )

    def _read_checkpoint_row(self, row: sqlite3.Row) -> JobCheckpoint:
        checkpoint_path = Path(row["payload_ref"])
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        validate_instance("job-checkpoint", payload)
        return JobCheckpoint.model_validate(payload)
