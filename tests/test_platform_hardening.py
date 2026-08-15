"""平台硬化（§6.3 条目 12）——SQLite WAL/FK、supervisor 隔离、legacy 认证与进程内限流。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from deep_research_agent.product.ratelimit import NullRateLimiter, TokenBucketRateLimiter
from deep_research_agent.research_jobs import ResearchJobService
from deep_research_agent.research_jobs.models import JobStatus, RuntimeStage
from legacy.workflows.states import CriticFeedback, ReportArtifact, RunMetrics, SourceRecord, TaskItem


LEGACY_KEY = "platform-hardening-master-key"


def _legacy_app(tmp_path: Path, *, ratelimiter=None, api_key: str | None = LEGACY_KEY):
    from deep_research_agent.gateway.api import create_app

    service = ResearchJobService(workspace_dir=str(tmp_path / "runtime"))
    kwargs = {"service_factory": lambda: service, "api_key": api_key}
    if ratelimiter is not None:
        kwargs["ratelimiter"] = ratelimiter
    return create_app(**kwargs), service


def _submit_payload() -> dict:
    return {
        "topic": "platform hardening smoke",
        "max_loops": 1,
        "research_profile": "default",
        "start_worker": False,
    }


def test_sqlite_database_enables_wal_and_foreign_keys(tmp_path: Path):
    """sqlite backend 连接应启用 WAL 与 foreign key 约束。"""
    from sqlalchemy import event as sqlalchemy_event, text

    from deep_research_agent.product.db import _sqlite_connect_pragmas, create_database

    database = create_database(
        f"sqlite+pysqlite:///{tmp_path / 'hardened.db'}",
        offline_mode=True,
    )
    assert sqlalchemy_event.contains(database.engine, "connect", _sqlite_connect_pragmas)
    database.create_schema()
    with database.engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert journal_mode == "wal"
    assert int(foreign_keys) == 1


def test_postgres_backend_does_not_attach_sqlite_pragmas(monkeypatch):
    """postgres backend 不应注册 sqlite 连接 pragma。"""
    import sqlalchemy

    from deep_research_agent.product import db as db_module
    from deep_research_agent.product.db import create_database

    recorded: list[tuple[str, object]] = []
    original_listen = sqlalchemy.event.listen

    def recording_listen(target, identifier, fn, *args, **kwargs):
        recorded.append((identifier, fn))
        return original_listen(target, identifier, fn, *args, **kwargs)

    monkeypatch.setattr(sqlalchemy.event, "listen", recording_listen)

    database = create_database("postgresql+psycopg://user:pass@localhost:5432/product")
    assert database.engine.dialect.name == "postgresql"
    assert all(fn is not db_module._sqlite_connect_pragmas for _, fn in recorded)


def _deterministic_orchestrator(service, job):
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

    source = SourceRecord(
        citation_id=1,
        source_type="web",
        query="platform hardening",
        title="可信深度研究 app",
        url="https://example.com/platform-hardening",
        snippet="平台硬化应保持 evidence 契约。",
        selected=True,
        trust_tier=4,
    )
    task = TaskItem(id=1, title="拆解任务", intent="规划", query="platform hardening")
    return ResearchJobOrchestrator(
        service=service,
        planner_fn=lambda state: {"tasks": [task], "status": "planned"},
        collect_step_fn=lambda state: (
            {"tasks": [task], "evidence_notes": [], "status": "researched"},
            False,
        ),
        verifier_fn=lambda state: {
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": state.get("memory_stats"),
            "run_metrics": state.get("run_metrics"),
            "status": "verified",
        },
        critic_fn=lambda state: {
            "critic_feedback": CriticFeedback(
                quality_score=8,
                is_sufficient=True,
                gaps=[],
                follow_up_queries=[],
                feedback="已足够",
            ),
            "loop_count": 1,
            "run_metrics": RunMetrics(status="reviewed"),
            "status": "reviewed",
        },
        writer_fn=lambda state: {
            "final_report": "# 报告\n\n平台硬化。[1]",
            "report_artifact": ReportArtifact(
                topic=state["research_topic"],
                report="# 报告\n\n平台硬化。[1]",
                citations=[source],
                metrics=RunMetrics(status="completed"),
            ),
            "status": "completed",
        },
    )


def test_corrupt_checkpoint_is_skipped_and_job_continues(tmp_path: Path):
    """单个损坏 checkpoint 文件应被跳过，job 其余任务仍正常执行。"""
    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="corrupt checkpoint",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )
    checkpoint_dir = service.store.checkpoint_dir(job.job_id)
    payload_file = next(checkpoint_dir.glob("*.json"))
    payload_file.write_text("{ not valid json", encoding="utf-8")

    assert service.store.get_latest_checkpoint(job.job_id) is None

    final_job = _deterministic_orchestrator(service, job).run(job.job_id)
    assert final_job.status == JobStatus.COMPLETED
    assert Path(final_job.report_path).exists()


def test_corrupt_latest_checkpoint_falls_back_to_previous_valid_one(tmp_path: Path):
    """最新 checkpoint 损坏时，应回退到上一个有效 checkpoint。"""
    from deep_research_agent.research_jobs.models import JobCheckpoint

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="checkpoint fallback",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )
    first = service.store.get_latest_checkpoint(job.job_id)
    assert first is not None

    second = service.store.save_checkpoint(
        JobCheckpoint(
            checkpoint_id=f"{job.job_id}-checkpoint-pending",
            job_id=job.job_id,
            stage=RuntimeStage.PLANNED,
            sequence=0,
            next_stage=RuntimeStage.COLLECTING,
            state_payload=first.state_payload,
        )
    )
    corrupted = service.store.checkpoint_dir(job.job_id) / f"{second.sequence:04d}-{second.stage.value}.json"
    corrupted.write_text("{ not valid json", encoding="utf-8")

    latest = service.store.get_latest_checkpoint(job.job_id)
    assert latest is not None
    assert latest.sequence == first.sequence


def test_corrupt_checkpoint_with_missing_fields_is_skipped(tmp_path: Path):
    """缺字段的 checkpoint 文件同样应被跳过。"""
    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="checkpoint missing fields",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )
    payload_file = next(service.store.checkpoint_dir(job.job_id).glob("*.json"))
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    del payload["state_payload"]
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    assert service.store.get_latest_checkpoint(job.job_id) is None


def test_worker_main_loop_marks_failed_job_instead_of_crash_looping(tmp_path: Path, monkeypatch):
    """worker 主循环异常应记录并标记 job 失败，而不是 crash-loop。"""
    from deep_research_agent.research_jobs import worker as worker_module

    real_service = ResearchJobService(workspace_dir=str(tmp_path))
    job = real_service.submit(
        topic="worker supervisor",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )

    class _ExplodingService:
        def __init__(self, *args, **kwargs) -> None:
            self.store = real_service.store
            self.get = real_service.get

        def configure_scheduler_factory(self, scheduler_factory) -> None:
            del scheduler_factory

        def run_job(self, job_id: str, *, worker_lease_id: str | None = None) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "ResearchJobService", _ExplodingService)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker",
            "--job-id",
            job.job_id,
            "--workspace-dir",
            str(tmp_path),
            "--runtime-dirname",
            "research_jobs",
            "--heartbeat-interval-seconds",
            "1",
            "--stale-timeout-seconds",
            "10",
        ],
    )

    worker_module.main()

    final = real_service.get(job.job_id)
    assert final is not None
    assert final.status == JobStatus.FAILED
    assert "boom" in (final.error or "")


def test_legacy_jobs_api_rejects_missing_and_wrong_api_key(tmp_path: Path):
    """legacy jobs API 应 fail closed：无 key / 错 key → 401，正确 key 通过。"""
    app, _ = _legacy_app(tmp_path)
    client = TestClient(app)

    missing = client.post("/v1/research/jobs", json=_submit_payload())
    assert missing.status_code == 401

    wrong = client.post(
        "/v1/research/jobs",
        headers={"X-API-Key": "wrong-key"},
        json=_submit_payload(),
    )
    assert wrong.status_code == 401

    accepted = client.post(
        "/v1/research/jobs",
        headers={"X-API-Key": LEGACY_KEY},
        json=_submit_payload(),
    )
    assert accepted.status_code == 202
    job_id = accepted.json()["job_id"]
    assert client.get(
        f"/v1/research/jobs/{job_id}",
        headers={"X-API-Key": LEGACY_KEY},
    ).status_code == 200
    assert client.get(f"/v1/research/jobs/{job_id}").status_code == 401


def test_legacy_jobs_api_fails_closed_when_no_key_configured(tmp_path: Path, monkeypatch):
    """未配置 master key 时 legacy jobs API 应 fail closed（503），不得无认证放行。"""
    monkeypatch.delenv("DEEP_RESEARCH_AGENT_MASTER_KEY", raising=False)
    app, _ = _legacy_app(tmp_path, api_key=None)
    client = TestClient(app)

    assert client.post("/v1/research/jobs", json=_submit_payload()).status_code == 503
    assert client.get("/v1/health").status_code == 200


def test_legacy_api_key_reads_master_key_from_environment(tmp_path: Path, monkeypatch):
    """create_app 未显式传 key 时，应从环境变量读取 master key。"""
    monkeypatch.setenv("DEEP_RESEARCH_AGENT_MASTER_KEY", "env-master-key")
    app, _ = _legacy_app(tmp_path, api_key=None)
    client = TestClient(app)

    assert client.post(
        "/v1/research/jobs",
        headers={"X-API-Key": "env-master-key"},
        json=_submit_payload(),
    ).status_code == 202
    assert client.post(
        "/v1/research/jobs",
        headers={"X-API-Key": "wrong"},
        json=_submit_payload(),
    ).status_code == 401


def test_legacy_create_rate_limit_returns_429_with_retry_after(tmp_path: Path):
    """超限请求应返回 429 与 Retry-After 头，且不同 route 独立计数。"""
    app, _ = _legacy_app(
        tmp_path,
        ratelimiter=TokenBucketRateLimiter(capacity=2, refill_rate=0.001),
    )
    client = TestClient(app)
    headers = {"X-API-Key": LEGACY_KEY}

    for _ in range(2):
        assert client.post("/v1/research/jobs", headers=headers, json=_submit_payload()).status_code == 202

    limited = client.post("/v1/research/jobs", headers=headers, json=_submit_payload())
    assert limited.status_code == 429
    retry_after = limited.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) >= 1

    batch = client.post(
        "/v1/batch/research",
        headers=headers,
        json={"jobs": [_submit_payload()]},
    )
    assert batch.status_code == 202


def test_login_rate_limit_returns_429(tmp_path: Path):
    """login 端点超限应返回 429。"""
    from deep_research_agent.gateway.api import create_app

    service = ResearchJobService(workspace_dir=str(tmp_path))
    app = create_app(
        service_factory=lambda: service,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'login-rate.db'}",
        offline_mode=True,
        api_key=LEGACY_KEY,
        ratelimiter=TokenBucketRateLimiter(capacity=1, refill_rate=0.001),
    )
    client = TestClient(app)
    credentials = {"email": "nobody@example.test", "password": "wrong password"}

    first = client.post("/v1/auth/login", json=credentials)
    assert first.status_code == 401

    second = client.post("/v1/auth/login", json=credentials)
    assert second.status_code == 429
    assert second.headers.get("Retry-After") is not None


def test_upload_rate_limit_is_scoped_per_tenant(tmp_path: Path):
    """upload 限流应按 (tenant_id, route) 独立计数。"""
    from deep_research_agent.gateway.api import create_app

    service = ResearchJobService(workspace_dir=str(tmp_path))
    app = create_app(
        service_factory=lambda: service,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'tenant-rate.db'}",
        offline_mode=True,
        api_key=LEGACY_KEY,
        ratelimiter=TokenBucketRateLimiter(capacity=3, refill_rate=0.001),
    )
    client_a = TestClient(app)
    client_b = TestClient(app)
    registered_a = client_a.post(
        "/v1/auth/register",
        json={"email": "a@example.test", "password": "password for tenant a 123"},
    )
    registered_b = client_b.post(
        "/v1/auth/register",
        json={"email": "b@example.test", "password": "password for tenant b 123"},
    )
    assert registered_a.status_code == 201
    assert registered_b.status_code == 201
    csrf_a = registered_a.json()["csrf_token"]
    csrf_b = registered_b.json()["csrf_token"]

    def upload(client: TestClient, csrf: str):
        return client.post(
            "/v1/corpus/upload",
            headers={"X-CSRF-Token": csrf},
            files={"file": ("doc.txt", b"tenant document", "text/plain")},
        )

    for _ in range(3):
        assert upload(client_a, csrf_a).status_code == 201

    assert upload(client_a, csrf_a).status_code == 429
    assert upload(client_b, csrf_b).status_code == 201


def test_rate_limit_can_be_disabled_for_test_mode(tmp_path: Path):
    """test mode 可注入零限流实现，请求不受限。"""
    app, _ = _legacy_app(tmp_path, ratelimiter=NullRateLimiter())
    client = TestClient(app)
    headers = {"X-API-Key": LEGACY_KEY}

    for _ in range(5):
        assert client.post("/v1/research/jobs", headers=headers, json=_submit_payload()).status_code == 202


def test_ratelimit_module_is_self_contained():
    """令牌桶应为纯进程内实现：线程安全且不依赖外部存储。"""
    import threading

    limiter = TokenBucketRateLimiter(capacity=50, refill_rate=0.001)
    results: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        local = []
        for _ in range(20):
            local.append(limiter.check("threads:v1.research.jobs") is None)
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 80
    assert results.count(True) == 50
