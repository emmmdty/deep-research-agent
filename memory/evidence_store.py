"""SQLite 证据记忆存储。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from legacy.workflows.states import EvidenceCluster, EvidenceUnit


class EvidenceStore:
    """用于持久化 verifier 产物的轻量 SQLite 存储。"""

    def __init__(self, workspace_dir: str = "workspace") -> None:
        self.root = Path(workspace_dir) / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "evidence.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_units (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_clusters (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save_evidence_units(self, topic: str, evidence_units: list[EvidenceUnit]) -> None:
        with self._connect() as conn:
            for unit in evidence_units:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evidence_units (id, topic, claim, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (unit.id, topic, unit.claim, json.dumps(unit.model_dump(), ensure_ascii=False)),
                )

    def save_evidence_clusters(self, topic: str, clusters: list[EvidenceCluster]) -> None:
        with self._connect() as conn:
            for cluster in clusters:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evidence_clusters (id, topic, claim, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (cluster.id, topic, cluster.claim, json.dumps(cluster.model_dump(), ensure_ascii=False)),
                )
