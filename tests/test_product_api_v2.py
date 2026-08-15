"""Product API authentication, tenancy, and decision-contract tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from deep_research_agent.gateway.api import create_app
from deep_research_agent.research_jobs import ResearchJobService


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"
LEGACY_MASTER_KEY = "product-api-v2-master-key"


@pytest.fixture
def app(tmp_path: Path):
    runtime_service = ResearchJobService(workspace_dir=str(tmp_path / "runtime"))
    return create_app(
        service_factory=lambda: runtime_service,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'product.db'}",
        offline_mode=True,
        bootstrap_admin_email=ADMIN_EMAIL,
        bootstrap_admin_password=ADMIN_PASSWORD,
        api_key=LEGACY_MASTER_KEY,
    )


@pytest.fixture
def admin(app) -> tuple[TestClient, str]:
    client = TestClient(app)
    response = client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return client, response.json()["csrf_token"]


def _accept_invite(
    admin_client: TestClient,
    admin_csrf: str,
    *,
    email: str,
    tenant_id: str,
    role: str = "user",
) -> tuple[TestClient, str]:
    invited = admin_client.post(
        "/v1/admin/invitations",
        headers={"X-CSRF-Token": admin_csrf},
        json={"email": email, "tenant_id": tenant_id, "role": role},
    )
    assert invited.status_code == 201
    token = invited.json()["invite_token"]
    accepted = TestClient(admin_client.app).post(
        f"/v1/auth/invitations/{token}/accept",
        json={"password": "user password with enough length"},
    )
    assert accepted.status_code == 201
    user_client = TestClient(admin_client.app)
    logged_in = user_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "user password with enough length"},
    )
    assert logged_in.status_code == 200
    return user_client, logged_in.json()["csrf_token"]


def _create_topic(client: TestClient, csrf: str, title: str = "Research topic") -> dict[str, Any]:
    response = client.post(
        "/v1/topics",
        headers={"X-CSRF-Token": csrf},
        json={"title": title},
    )
    assert response.status_code == 201
    return response.json()


def test_database_rejects_sqlite_without_explicit_offline_mode():
    from deep_research_agent.product.db import create_database

    with pytest.raises(ValueError, match="PostgreSQL"):
        create_database("sqlite+pysqlite:///:memory:", offline_mode=False)


def test_offline_registration_persists_in_local_database_and_production_stays_invite_only(
    tmp_path: Path, monkeypatch
):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'persistent-product.db'}"
    monkeypatch.setenv("PRODUCT_DATABASE_URL", database_url)
    monkeypatch.setenv("PRODUCT_OFFLINE_MODE", "true")
    first_runtime = ResearchJobService(workspace_dir=str(tmp_path / "runtime-one"))
    first_app = create_app(service_factory=lambda: first_runtime)
    first_client = TestClient(first_app)
    assert first_client.get("/v1/auth/registration-status").json() == {"enabled": True}
    registered = first_client.post(
        "/v1/auth/register",
        json={"email": "local-user@example.test", "password": "local demo password 123"},
    )
    assert registered.status_code == 201
    assert registered.json()["user"]["role"] == "admin"
    assert (tmp_path / "persistent-product.db").exists()

    second_runtime = ResearchJobService(workspace_dir=str(tmp_path / "runtime-two"))
    second_app = create_app(service_factory=lambda: second_runtime)
    second_client = TestClient(second_app)
    logged_in = second_client.post(
        "/v1/auth/login",
        json={"email": "local-user@example.test", "password": "local demo password 123"},
    )
    assert logged_in.status_code == 200

    invite_only_app = create_app(
        service_factory=lambda: ResearchJobService(workspace_dir=str(tmp_path / "runtime-three")),
        database_url=database_url,
        offline_mode=True,
        allow_public_registration=False,
    )
    invite_only_client = TestClient(invite_only_app)
    assert invite_only_client.get("/v1/auth/registration-status").json() == {"enabled": False}
    assert invite_only_client.post(
        "/v1/auth/register",
        json={"email": "blocked@example.test", "password": "local demo password 123"},
    ).status_code == 404


def test_fresh_alembic_upgrade_handles_dynamic_legacy_schema(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    inspector = inspect(create_engine(database_url))
    columns = {column["name"] for column in inspector.get_columns("product_memories")}
    assert {"subject_id", "key", "provenance", "sensitivity", "expires_at", "confirmed"} <= columns


def test_invitation_login_logout_and_cookie_security(app):
    admin_client = TestClient(app)
    login = admin_client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )

    assert login.status_code == 200
    assert login.json()["user"]["role"] == "admin"
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie

    csrf = login.json()["csrf_token"]
    user_client, user_csrf = _accept_invite(
        admin_client,
        csrf,
        email="member@example.test",
        tenant_id="tenant-one",
    )
    session = user_client.get("/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["user"]["email"] == "member@example.test"

    missing_csrf = user_client.post("/v1/auth/logout")
    assert missing_csrf.status_code == 403
    logout = user_client.post(
        "/v1/auth/logout",
        headers={"X-CSRF-Token": user_csrf},
    )
    assert logout.status_code == 204
    assert user_client.get("/v1/auth/session").status_code == 401


def test_role_checks_and_csrf_are_enforced(admin):
    admin_client, admin_csrf = admin
    user_client, user_csrf = _accept_invite(
        admin_client,
        admin_csrf,
        email="plain-user@example.test",
        tenant_id="tenant-role",
    )

    denied = user_client.post(
        "/v1/admin/invitations",
        headers={"X-CSRF-Token": user_csrf},
        json={"email": "other@example.test", "tenant_id": "tenant-role", "role": "user"},
    )
    assert denied.status_code == 403
    assert user_client.post("/v1/topics", json={"title": "No CSRF"}).status_code == 403


def test_topic_and_run_reads_are_tenant_scoped(admin):
    admin_client, admin_csrf = admin
    first, first_csrf = _accept_invite(
        admin_client,
        admin_csrf,
        email="first@example.test",
        tenant_id="tenant-first",
    )
    second, _ = _accept_invite(
        admin_client,
        admin_csrf,
        email="second@example.test",
        tenant_id="tenant-second",
    )
    topic = _create_topic(first, first_csrf)
    run = first.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": first_csrf},
        json={"question": "Compare the available evidence"},
    )
    assert run.status_code == 202

    assert second.get(f"/v1/topics/{topic['topic_id']}").status_code == 404
    assert second.get(f"/v1/runs/{run.json()['run_id']}").status_code == 404


def test_message_decisions_are_exact_and_include_structured_briefs(admin):
    client, csrf = admin
    topic = _create_topic(client, csrf)
    conversation_id = topic["conversation_id"]

    direct = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "What is 2 + 2?"},
    )
    assert direct.status_code == 200
    assert direct.json()["response_type"] == "direct_answer"

    ambiguous = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Research it"},
    )
    assert ambiguous.status_code == 200
    assert ambiguous.json()["response_type"] == "clarification_required"

    complex_definition = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "什么是事件图谱、Agent与LLM如何相互作用？"},
    )
    assert complex_definition.status_code == 202
    assert complex_definition.json()["response_type"] == "research_job_started"

    expensive = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Exhaustively compare every paper ever published"},
    )
    assert expensive.status_code == 200
    assert expensive.json()["response_type"] == "clarification_required"

    refresh = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Update the evidence for this topic", "refresh": True},
    )
    assert refresh.status_code == 202
    assert refresh.json()["response_type"] == "research_job_started"

    explicit_refresh_wins = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Research it", "refresh": True},
    )
    assert explicit_refresh_wins.status_code == 202
    assert explicit_refresh_wins.json()["response_type"] == "research_job_started"

    allowed = {"direct_answer", "clarification_required", "research_job_started"}
    for response in (direct, ambiguous, expensive, refresh, explicit_refresh_wins):
        body = response.json()
        assert body["response_type"] in allowed
        assert set(body["brief"]) == {
            "brief_id",
            "run_id",
            "question",
            "objectives",
            "constraints",
            "snapshot_cutoff",
        }


def test_message_router_handles_chinese_intent_without_whitespace(admin, app):
    client, csrf = admin
    topic = _create_topic(client, csrf, "事件图谱 Agent LLM")
    conversation_id = topic["conversation_id"]

    research = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "分析事件图谱、Agent与LLM如何相互作用，聚焦论文证据"},
    )
    assert research.status_code == 202
    assert research.json()["response_type"] == "research_job_started"

    ambiguous = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "研究一下"},
    )
    assert ambiguous.status_code == 200
    assert ambiguous.json()["response_type"] == "clarification_required"

    app.state.product_service.complete_run(
        research.json()["run_id"],
        tenant_id="system",
        bundle={"report_markdown": "事件图谱证据快照", "schema_version": "2.0"},
        snapshot_cutoff="2026-07-18T00:00:00+00:00",
    )
    follow_up = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "总结事件图谱的证据"},
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["answer"] == "事件图谱证据快照"
    assert follow_up.json()["brief"]["snapshot_cutoff"] == "2026-07-18T00:00:00+00:00"

    direct = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "什么是事件图谱？"},
    )
    assert direct.status_code == 200
    assert direct.json()["response_type"] == "direct_answer"

    greeting = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "你好"},
    )
    assert greeting.status_code == 200
    assert greeting.json()["response_type"] == "direct_answer"


def test_follow_up_uses_frozen_snapshot_until_refresh(admin, app):
    client, csrf = admin
    topic = _create_topic(client, csrf)
    conversation_id = topic["conversation_id"]
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Establish a trusted baseline"},
    ).json()
    app.state.product_service.complete_run(
        run["run_id"],
        tenant_id=run["tenant_id"],
        bundle={"report_markdown": "Frozen evidence answer", "schema_version": "2.0"},
        snapshot_cutoff="2026-07-17T12:00:00+00:00",
    )

    quick = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Summarize the trusted baseline"},
    )
    assert quick.status_code == 200
    assert quick.json()["response_type"] == "direct_answer"
    assert quick.json()["brief"]["snapshot_cutoff"] == "2026-07-17T12:00:00+00:00"

    simple = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "What is 3 + 4?"},
    )
    assert simple.status_code == 200
    assert simple.json()["response_type"] == "direct_answer"
    assert simple.json()["answer"] == "7"
    assert simple.json()["brief"]["snapshot_cutoff"] is None

    unrelated = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Analyze quantum error correction benchmarks in 2026"},
    )
    assert unrelated.status_code == 202
    assert unrelated.json()["response_type"] == "research_job_started"
    assert unrelated.json()["brief"]["snapshot_cutoff"] is None

    refresh = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Summarize the trusted baseline", "refresh": True},
    )
    assert refresh.status_code == 202
    assert refresh.json()["response_type"] == "research_job_started"
    assert refresh.json()["run_id"] != run["run_id"]


def test_private_corpus_memory_crud_and_export_are_tenant_scoped(admin):
    admin_client, admin_csrf = admin
    owner, owner_csrf = _accept_invite(
        admin_client,
        admin_csrf,
        email="owner@example.test",
        tenant_id="tenant-owner",
    )
    outsider, _ = _accept_invite(
        admin_client,
        admin_csrf,
        email="outsider@example.test",
        tenant_id="tenant-outsider",
    )

    uploaded = owner.post(
        "/v1/corpus/upload",
        headers={"X-CSRF-Token": owner_csrf},
        files={"file": ("notes.txt", b"private research notes", "text/plain")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["visibility"] == "private"
    assert outsider.get(f"/v1/corpus/{uploaded.json()['document_id']}").status_code == 404

    created = owner.post(
        "/v1/memory",
        headers={"X-CSRF-Token": owner_csrf},
        json={"scope": "user_memory", "content": "Prefer primary sources", "confidence": 0.9},
    )
    assert created.status_code == 201
    memory_id = created.json()["memory_id"]
    updated = owner.patch(
        f"/v1/memory/{memory_id}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"content": "Prefer peer-reviewed primary sources"},
    )
    assert updated.status_code == 200
    assert outsider.get(f"/v1/memory/{memory_id}").status_code == 404
    exported = owner.get("/v1/memory/export")
    assert exported.status_code == 200
    assert exported.json()["memories"][0]["memory_id"] == memory_id
    assert owner.delete(
        f"/v1/memory/{memory_id}", headers={"X-CSRF-Token": owner_csrf}
    ).status_code == 204


def test_private_corpus_is_frozen_into_scheduler_job_and_bundle(admin):
    from configs.settings import Settings
    from deep_research_agent.research_jobs.worker import build_scheduler_factory

    client, csrf = admin
    uploaded = client.post(
        "/v1/corpus/upload",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("notes.txt", b"trusted private notes", "text/plain")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["document_id"]
    topic = _create_topic(client, csrf)
    created = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={
            "question": "Use the uploaded evidence",
            "corpus_document_ids": [document_id],
            "start_worker": False,
        },
    )
    assert created.status_code == 202
    runtime_job = client.app.state.runtime_service.get(created.json()["research_job_id"])
    assert runtime_job.metadata["corpus_manifest"]["document_version_ids"] == [document_id]
    assert runtime_job.metadata["config_snapshot"]["file_inputs"]
    staged = Path(runtime_job.metadata["config_snapshot"]["file_inputs"][0])
    assert staged.read_bytes() == b"trusted private notes"

    client.app.state.runtime_service.configure_scheduler_factory(
        build_scheduler_factory(Settings(scheduler_runtime_mode="offline"), offline=True)
    )
    client.app.state.runtime_service.run_job(runtime_job.job_id)
    bundle = client.get(f"/v1/runs/{created.json()['run_id']}/bundle")
    assert bundle.status_code == 200
    assert bundle.json()["corpus_manifest"]["document_version_ids"] == [document_id]


def test_memory_requires_sensitive_confirmation_and_expires_or_supersedes(admin, app):
    client, csrf = admin
    rejected = client.post(
        "/v1/memory",
        headers={"X-CSRF-Token": csrf},
        json={"scope": "user_memory", "key": "profile", "content": "private", "sensitivity": "sensitive"},
    )
    assert rejected.status_code == 422
    first = client.post(
        "/v1/memory",
        headers={"X-CSRF-Token": csrf},
        json={
            "scope": "user_memory",
            "key": "profile",
            "content": "prefers primary papers",
            "provenance": {"source": "user"},
            "sensitivity": "sensitive",
            "confirm_sensitive": True,
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/v1/memory",
        headers={"X-CSRF-Token": csrf},
        json={"scope": "user_memory", "key": "profile", "content": "prefers ACL papers"},
    )
    assert second.status_code == 201
    assert client.get(f"/v1/memory/{first.json()['memory_id']}").json()["status"] == "superseded"
    assert second.json()["supersedes_memory_id"] == first.json()["memory_id"]
    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Use remembered preferences", "start_worker": False},
    ).json()
    runtime_job = app.state.runtime_service.get(run["research_job_id"])
    memory_context = runtime_job.metadata["research_brief"]["constraints"]["memory_context"]
    assert memory_context[0]["key"] == "profile"
    assert memory_context[0]["content"] == "prefers ACL papers"
    expiring = client.post(
        "/v1/memory",
        headers={"X-CSRF-Token": csrf},
        json={
            "scope": "conversation_focus",
            "subject_id": topic["conversation_id"],
            "content": "temporary focus",
            "ttl_seconds": 1,
        },
    )
    assert expiring.status_code == 201
    memory_id = expiring.json()["memory_id"]
    identity = app.state.product_service.auth.authenticate(client.cookies.get("dra_session"))
    assert identity is not None
    app.state.product_service.repository.update_memory(
        memory_id,
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        values={"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
    )
    assert not any(item["memory_id"] == memory_id for item in client.get("/v1/memory").json()["memories"])


def test_admin_model_secrets_are_redacted_and_running_config_is_frozen(admin):
    client, csrf = admin
    headers = {"X-CSRF-Token": csrf}
    model = client.post(
        "/v1/admin/models",
        headers=headers,
        json={
            "endpoint_id": "planner-primary",
            "base_url": "https://models.example.test/v1",
            "model": "research-model",
            "api_key": "top-secret-model-key",
        },
    )
    assert model.status_code == 201
    assert "top-secret-model-key" not in model.text
    assert model.json()["api_key"] == "[redacted]"
    assert "top-secret-model-key" not in client.get("/v1/admin/models").text

    unsafe = client.post(
        "/v1/admin/configs",
        headers=headers,
        json={
            "version_id": "unsafe-runtime",
            "config": {
                "Authorization": "Bearer hidden-auth",
                "privateKey": "hidden-private-key",
                "access-key": "hidden-access-key",
                "bearer": "hidden-bearer",
                "refresh_token": "hidden-refresh-token",
                "model_token": "hidden-model-token",
                "client_secret_key": "hidden-client-secret",
            },
        },
    )
    assert unsafe.status_code == 409

    for version in ("runtime-v1", "runtime-v2"):
        created = client.post(
            "/v1/admin/configs",
            headers=headers,
            json={
                "version_id": version,
                "config": {
                    "planner_endpoint_id": "planner-primary",
                    "domain_pack_id": "event-graph-agents-llms",
                    "max_loops": 2,
                    "planner_credential_id": "planner-credential-ref",
                    "token_budget": 10_000,
                },
            },
        )
        assert created.status_code == 201
    assert client.post("/v1/admin/configs/runtime-v1:activate", headers=headers).status_code == 200

    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers=headers,
        json={"question": "Freeze this configuration"},
    ).json()
    assert run["config_version_id"] == "runtime-v1"
    assert "config_snapshot" not in run
    runtime_job = client.app.state.runtime_service.get(run["research_job_id"])
    assert runtime_job.runtime_path == "scheduler-v2"
    assert runtime_job.metadata["config_snapshot"]["planner_endpoint_id"] == "planner-primary"
    assert "product_config_snapshot" not in runtime_job.metadata

    assert client.post("/v1/admin/configs/runtime-v2:activate", headers=headers).status_code == 200
    loaded = client.get(f"/v1/runs/{run['run_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["config_version_id"] == "runtime-v1"
    assert "config_snapshot" not in loaded.json()
    config_response = client.get("/v1/admin/configs")
    assert not any(
        secret in config_response.text
        for secret in ("hidden-auth", "hidden-private-key", "hidden-access-key", "hidden-bearer")
    )


def test_product_run_delegates_to_canonical_runtime_and_syncs_artifacts(admin, app):
    from deep_research_agent.research_jobs.models import JobStatus, RuntimeStage

    client, csrf = admin
    topic = _create_topic(client, csrf)
    created = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Run the canonical research planner", "start_worker": False},
    )
    assert created.status_code == 202
    body = created.json()
    runtime_service = app.state.runtime_service
    runtime_job = runtime_service.get(body["research_job_id"])
    assert runtime_job is not None
    assert runtime_job.topic == "Run the canonical research planner"

    bundle = {"schema_version": "2.0", "report_markdown": "Canonical runtime bundle"}
    bundle_path = Path(runtime_job.report_bundle_path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(__import__("json").dumps(bundle), encoding="utf-8")
    runtime_service.store.update_job_status(
        runtime_job.job_id,
        status=JobStatus.COMPLETED,
        current_stage=RuntimeStage.COMPLETED,
    )

    synced = client.get(f"/v1/runs/{body['run_id']}")
    assert synced.status_code == 200
    assert synced.json()["status"] == "completed"
    assert client.get(f"/v1/runs/{body['run_id']}/bundle").json() == bundle


def test_run_event_dedupe_is_safe_under_concurrent_sync(admin, app):
    client, csrf = admin
    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Concurrent event sync", "start_worker": False},
    ).json()

    def append_once(_: int) -> dict[str, Any]:
        return app.state.product_service.append_run_event(
            run["run_id"],
            tenant_id=run["tenant_id"],
            event_type="runtime.task.started",
            payload={"task_id": "research-01"},
            dedupe_key="runtime-event:event-0001",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(append_once, range(16)))

    assert len({result["sequence"] for result in results}) == 1
    events = app.state.product_service.list_run_events(
        run["run_id"], tenant_id=run["tenant_id"]
    )
    assert [event["event_type"] for event in events].count("runtime.task.started") == 1


def test_completed_scheduler_run_emits_an_honest_report_bundle(admin, app):
    from configs.settings import Settings
    from deep_research_agent.research_jobs.worker import build_scheduler_factory

    client, csrf = admin
    app.state.runtime_service.configure_scheduler_factory(
        build_scheduler_factory(Settings(scheduler_runtime_mode="offline"), offline=True)
    )
    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Trace event graph and agent interactions", "start_worker": False},
    ).json()

    app.state.runtime_service.run_job(run["research_job_id"])

    synced = client.get(f"/v1/runs/{run['run_id']}")
    bundle = client.get(f"/v1/runs/{run['run_id']}/bundle")
    assert synced.json()["status"] == "completed"
    assert bundle.status_code == 200
    assert bundle.json()["schema_version"] == "2.0"
    assert "No evidence-backed conclusion" in bundle.json()["report_markdown"]
    assert bundle.json()["accepted_claims"] == []


def test_product_cancel_and_resume_delegate_to_canonical_runtime(admin, app):
    client, csrf = admin
    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Delegated lifecycle", "start_worker": False},
    ).json()

    cancelled = client.post(
        f"/v1/runs/{run['run_id']}:cancel", headers={"X-CSRF-Token": csrf}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert app.state.runtime_service.get(run["research_job_id"]).status.value == "cancelled"
    events = app.state.product_service.list_run_events(
        run["run_id"], tenant_id=run["tenant_id"]
    )
    assert [event["event_type"] for event in events].count("run.cancelled") == 1

    resumed = client.post(
        f"/v1/runs/{run['run_id']}:resume",
        headers={"X-CSRF-Token": csrf},
        json={"start_worker": False},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "created"
    assert app.state.runtime_service.get(run["research_job_id"]).status.value == "created"


def test_product_runtime_jobs_are_not_exposed_through_legacy_gateway(admin):
    client, csrf = admin
    legacy_headers = {"X-API-Key": LEGACY_MASTER_KEY}
    topic = _create_topic(client, csrf)
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Tenant-scoped runtime job", "start_worker": False},
    ).json()
    runtime_job_id = run["research_job_id"]

    assert client.get(
        f"/v1/research/jobs/{runtime_job_id}", headers=legacy_headers
    ).status_code == 404
    assert client.get(
        f"/v1/research/jobs/{runtime_job_id}/events", headers=legacy_headers
    ).status_code == 404
    assert client.get(
        f"/v1/research/jobs/{runtime_job_id}/bundle", headers=legacy_headers
    ).status_code == 404
    assert client.post(
        f"/v1/research/jobs/{runtime_job_id}:cancel",
        json={},
        headers=legacy_headers,
    ).status_code == 404


def test_run_rejects_conversation_from_another_topic(admin):
    client, csrf = admin
    first = _create_topic(client, csrf, "First topic")
    second = _create_topic(client, csrf, "Second topic")

    response = client.post(
        "/v1/runs",
        headers={"X-CSRF-Token": csrf},
        json={
            "topic_id": first["topic_id"],
            "conversation_id": second["conversation_id"],
            "question": "Invalid cross-topic conversation",
            "start_worker": False,
        },
    )

    assert response.status_code == 422


def test_whitespace_only_product_inputs_are_validation_errors(app):
    client = TestClient(app, raise_server_exceptions=False)
    login = client.post(
        "/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    assert client.post("/v1/topics", headers=headers, json={"title": "   "}).status_code == 422
    topic = client.post("/v1/topics", headers=headers, json={"title": "Valid"}).json()
    assert client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers=headers,
        json={"question": "  ", "start_worker": False},
    ).status_code == 422
    assert client.post(
        f"/v1/conversations/{topic['conversation_id']}/messages",
        headers=headers,
        json={"content": "  "},
    ).status_code == 422


def test_bootstrap_admin_can_be_configured_by_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_EMAIL", "env-admin@example.test")
    monkeypatch.setenv("DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_PASSWORD", "environment admin password")
    app = create_app(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'env-product.db'}",
        offline_mode=True,
        service_factory=lambda: ResearchJobService(workspace_dir=str(tmp_path / "env-runtime")),
    )

    login = TestClient(app).post(
        "/v1/auth/login",
        json={"email": "env-admin@example.test", "password": "environment admin password"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "admin"


def test_bootstrap_admin_environment_requires_both_values(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_EMAIL", "env-admin@example.test")
    monkeypatch.delenv("DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="both"):
        create_app(
            database_url=f"sqlite+pysqlite:///{tmp_path / 'invalid-env-product.db'}",
            offline_mode=True,
            service_factory=lambda: ResearchJobService(workspace_dir=str(tmp_path / "invalid-runtime")),
        )
