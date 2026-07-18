"""Product API authentication, tenancy, and decision-contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from deep_research_agent.gateway.api import create_app


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture
def app(tmp_path: Path):
    return create_app(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'product.db'}",
        offline_mode=True,
        bootstrap_admin_email=ADMIN_EMAIL,
        bootstrap_admin_password=ADMIN_PASSWORD,
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

    for version in ("runtime-v1", "runtime-v2"):
        created = client.post(
            "/v1/admin/configs",
            headers=headers,
            json={"version_id": version, "config": {"planner_endpoint_id": "planner-primary"}},
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

    assert client.post("/v1/admin/configs/runtime-v2:activate", headers=headers).status_code == 200
    loaded = client.get(f"/v1/runs/{run['run_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["config_version_id"] == "runtime-v1"
