"""Phase 04 审计侧车产物持久化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deep_research_agent.auditor.models import ClaimReviewQueue
from deep_research_agent.reporting.schemas import validate_instance


def audit_dir(job_workspace_dir: str | Path) -> Path:
    """返回当前 job 的 audit 目录。"""
    path = Path(job_workspace_dir) / "audit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_claim_graph(job_workspace_dir: str | Path, payload: dict[str, Any]) -> Path:
    """写出 claim graph 侧车文件。"""
    path = audit_dir(job_workspace_dir) / "claim_graph.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_review_queue(job_workspace_dir: str | Path, payload: dict[str, Any]) -> Path:
    """写出 review queue 并执行 schema 校验。"""
    queue = ClaimReviewQueue.model_validate(payload)
    queue_payload = queue.model_dump(mode="json")
    validate_instance("claim-review-queue", queue_payload)
    for item in queue_payload["items"]:
        validate_instance("critical-claim-review-item", item)
    path = audit_dir(job_workspace_dir) / "review_queue.json"
    path.write_text(json.dumps(queue_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
