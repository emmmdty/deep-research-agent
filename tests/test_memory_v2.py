from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def test_memory_ttl_sensitive_confirmation_and_conflict_supersession():
    from deep_research_agent.memory_v2.models import MemoryScope
    from deep_research_agent.memory_v2.service import MemoryService

    service = MemoryService()
    first = service.write(
        tenant_id="tenant-a",
        subject_id="user-a",
        scope=MemoryScope.USER_MEMORY,
        key="preferred-model",
        content="small model",
        provenance={"run_id": "run-1"},
        ttl_seconds=60,
    )
    second = service.write(
        tenant_id="tenant-a",
        subject_id="user-a",
        scope="user_memory",
        key="preferred-model",
        content="large model",
        provenance={"run_id": "run-2"},
    )
    assert second.status == "active"
    assert service.get(first.memory_id, tenant_id="tenant-a").status == "superseded"

    with pytest.raises(PermissionError):
        service.write(
            tenant_id="tenant-a",
            subject_id="user-a",
            scope="user_memory",
            key="email",
            content="a@example.com",
            sensitivity="sensitive",
        )

    confirmed = service.write(
        tenant_id="tenant-a",
        subject_id="user-a",
        scope="user_memory",
        key="email",
        content="a@example.com",
        sensitivity="sensitive",
        confirmed=True,
    )
    assert confirmed.expires_at is not None
    assert confirmed.provenance == {}


def test_memory_expiry_cross_tenant_denial_and_user_export_delete():
    from deep_research_agent.memory_v2.service import MemoryService

    now = datetime.now(timezone.utc)
    service = MemoryService(clock=lambda: now)
    record = service.write(
        tenant_id="tenant-a",
        subject_id="user-a",
        scope="conversation_focus",
        key="focus",
        content="current project",
        ttl_seconds=1,
    )
    with pytest.raises(PermissionError):
        service.search("project", tenant_id="tenant-b")
    assert service.export_user("user-a", tenant_id="tenant-a")[0].memory_id == record.memory_id

    service.clock = lambda: now + timedelta(seconds=2)
    assert service.search("project", tenant_id="tenant-a") == []
    assert service.delete_user("user-a", tenant_id="tenant-a") == 1
    assert service.export_user("user-a", tenant_id="tenant-a") == []
