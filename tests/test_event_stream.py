"""Reconnectable, tenant-scoped product event stream tests."""

from __future__ import annotations

from pathlib import Path
import threading
import time

import pytest
from fastapi.testclient import TestClient

from deep_research_agent.gateway.api import create_app
from deep_research_agent.research_jobs import ResearchJobService


@pytest.fixture
def product(tmp_path: Path):
    runtime_service = ResearchJobService(workspace_dir=str(tmp_path / "runtime"))
    app = create_app(
        service_factory=lambda: runtime_service,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'events.db'}",
        offline_mode=True,
        event_poll_interval_seconds=0.01,
        event_heartbeat_interval_seconds=0.02,
        event_stream_timeout_seconds=0.25,
        bootstrap_admin_email="admin@example.test",
        bootstrap_admin_password="correct horse battery staple",
    )
    client = TestClient(app)
    login = client.post(
        "/v1/auth/login",
        json={"email": "admin@example.test", "password": "correct horse battery staple"},
    )
    csrf = login.json()["csrf_token"]
    topic = client.post(
        "/v1/topics",
        headers={"X-CSRF-Token": csrf},
        json={"title": "Event stream topic"},
    ).json()
    run = client.post(
        f"/v1/topics/{topic['topic_id']}/runs",
        headers={"X-CSRF-Token": csrf},
        json={"question": "Stream ordered progress"},
    ).json()
    return app, client, csrf, run


def _event_ids(body: str) -> list[int]:
    return [int(line.removeprefix("id: ")) for line in body.splitlines() if line.startswith("id: ")]


def test_sse_delivers_ordered_monotonic_events_without_duplicates(product):
    app, client, _, run = product
    service = app.state.product_service
    service.append_run_event(
        run["run_id"], tenant_id=run["tenant_id"], event_type="task.started", payload={"task_id": "a"}
    )
    service.append_run_event(
        run["run_id"], tenant_id=run["tenant_id"], event_type="task.completed", payload={"task_id": "a"}
    )

    response = client.get(f"/v1/runs/{run['run_id']}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    ids = _event_ids(response.text)
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert "event: run.created" in response.text
    assert "event: task.completed" in response.text


def test_sse_reconnect_uses_last_event_id_and_emits_heartbeat(product):
    app, client, _, run = product
    service = app.state.product_service
    second = service.append_run_event(
        run["run_id"], tenant_id=run["tenant_id"], event_type="task.started", payload={}
    )
    third = service.append_run_event(
        run["run_id"], tenant_id=run["tenant_id"], event_type="task.completed", payload={}
    )

    resumed = client.get(
        f"/v1/runs/{run['run_id']}/events",
        headers={"Last-Event-ID": str(second["sequence"])},
    )
    assert _event_ids(resumed.text) == [third["sequence"]]
    assert "event: task.completed" in resumed.text

    caught_up = client.get(
        f"/v1/runs/{run['run_id']}/events",
        headers={"Last-Event-ID": str(third["sequence"])},
    )
    assert ": heartbeat" in caught_up.text
    assert _event_ids(caught_up.text) == []


def test_sse_terminal_event_closes_snapshot_stream(product):
    app, client, _, run = product
    app.state.product_service.complete_run(
        run["run_id"],
        tenant_id=run["tenant_id"],
        bundle={"schema_version": "2.0", "report_markdown": "done"},
        snapshot_cutoff="2026-07-18T00:00:00+00:00",
    )

    response = client.get(f"/v1/runs/{run['run_id']}/events")

    assert response.status_code == 200
    assert "event: run.completed" in response.text
    assert "\"terminal\":true" in response.text


def test_sse_denies_cross_tenant_access(product):
    app, owner, csrf, run = product
    invited = owner.post(
        "/v1/admin/invitations",
        headers={"X-CSRF-Token": csrf},
        json={"email": "other@example.test", "tenant_id": "other-tenant", "role": "user"},
    ).json()
    other = TestClient(app)
    other.post(
        f"/v1/auth/invitations/{invited['invite_token']}/accept",
        json={"password": "other password with length"},
    )
    other.post(
        "/v1/auth/login",
        json={"email": "other@example.test", "password": "other password with length"},
    )

    denied = other.get(f"/v1/runs/{run['run_id']}/events")

    assert denied.status_code == 404


def test_sse_waits_for_events_appended_after_connection(product):
    app, client, _, run = product
    service = app.state.product_service
    initial = service.list_run_events(run["run_id"], tenant_id=run["tenant_id"])
    assert initial
    output: dict[str, object] = {}

    def consume() -> None:
        response = client.get(
            f"/v1/runs/{run['run_id']}/events",
            headers={"Last-Event-ID": str(initial[-1]["sequence"])},
        )
        output["status"] = response.status_code
        output["text"] = response.text

    reader = threading.Thread(target=consume)
    reader.start()
    time.sleep(0.05)
    service.append_run_event(
        run["run_id"],
        tenant_id=run["tenant_id"],
        event_type="task.completed",
        payload={"task_id": "late"},
    )
    service.complete_run(
        run["run_id"],
        tenant_id=run["tenant_id"],
        bundle={"schema_version": "2.0", "report_markdown": "done"},
        snapshot_cutoff="2026-07-18T00:00:00+00:00",
    )
    reader.join(timeout=1)

    assert not reader.is_alive()
    assert output["status"] == 200
    assert ": heartbeat" in str(output["text"])
    assert "event: task.completed" in str(output["text"])
    assert "event: run.completed" in str(output["text"])
