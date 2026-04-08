"""Tests for package update behavior."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models import Package, PackageStatusUpdate, User
from app.services.package_service import PackageService


class _FakeWriteQueue:
    def __init__(self, fail_first: bool = False, fail_all: bool = False):
        self.fail_first = fail_first
        self.fail_all = fail_all
        self.calls: list[tuple[str, list[str | None]]] = []
        self.queue = asyncio.Queue()

    async def execute(self, query, params, return_result=False):
        self.calls.append((query, params))
        if self.fail_all:
            raise Exception('Constraint Error: Duplicate key "id: abc" violates primary key constraint')
        if self.fail_first:
            self.fail_first = False
            raise Exception('Constraint Error: Duplicate key "id: abc" violates primary key constraint')
        return None


async def _return_queue(queue):
    return queue


@pytest.mark.asyncio
async def test_update_status_retries_with_merge_on_duplicate_key(monkeypatch):
    service = PackageService()
    package_id = uuid4()
    recipient_id = uuid4()
    actor_id = uuid4()
    now = datetime.now(UTC)

    original = Package(
        id=package_id,
        tracking_no="TRACK-1001",
        carrier="UPS",
        recipient_id=recipient_id,
        status="awaiting_pickup",
        notes="ready",
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    updated = original.model_copy(update={"status": "delivered", "notes": "done"})
    actor = User(
        id=actor_id,
        username="admin",
        password_hash="hash",
        full_name="Admin User",
        role="admin",
        is_active=True,
        must_change_password=False,
        password_history=None,
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )
    queue = _FakeWriteQueue(fail_first=True)
    package_event_calls: list[tuple] = []
    audit_calls: list[tuple] = []

    async def fake_get_package_by_id(target_id):
        assert target_id == package_id
        if len(queue.calls) >= 2:
            return updated
        return original

    async def fake_create_package_event(**kwargs):
        package_event_calls.append((kwargs["old_status"], kwargs["new_status"], kwargs["notes"]))

    async def fake_log_package_event(**kwargs):
        audit_calls.append((kwargs["old_status"], kwargs["new_status"], kwargs["notes"]))

    monkeypatch.setattr(service, "get_package_by_id", fake_get_package_by_id)
    monkeypatch.setattr(service, "_create_package_event", fake_create_package_event)
    monkeypatch.setattr("app.services.package_service.get_write_queue", lambda: _return_queue(queue))
    monkeypatch.setattr("app.services.package_service.audit_service.log_package_event", fake_log_package_event)

    result = await service.update_status(
        package_id=package_id,
        status_update=PackageStatusUpdate(status="delivered", notes="done"),
        actor=actor,
    )

    assert result.status == "delivered"
    assert len(queue.calls) == 2
    assert "update packages" in queue.calls[0][0].lower()
    assert "insert into packages" in queue.calls[1][0].lower()
    assert "on conflict (id) do update" in queue.calls[1][0].lower()
    assert package_event_calls == [("awaiting_pickup", "delivered", "done")]
    assert audit_calls == [("awaiting_pickup", "delivered", "done")]


@pytest.mark.asyncio
async def test_update_status_does_not_create_event_when_update_and_merge_fail(monkeypatch):
    service = PackageService()
    package_id = uuid4()
    recipient_id = uuid4()
    actor_id = uuid4()
    now = datetime.now(UTC)

    original = Package(
        id=package_id,
        tracking_no="TRACK-1002",
        carrier="FedEx",
        recipient_id=recipient_id,
        status="out_for_delivery",
        notes="en route",
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    actor = User(
        id=actor_id,
        username="admin",
        password_hash="hash",
        full_name="Admin User",
        role="admin",
        is_active=True,
        must_change_password=False,
        password_history=None,
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )
    queue = _FakeWriteQueue(fail_all=True)
    package_event_calls: list[dict] = []
    audit_calls: list[dict] = []

    async def fake_get_package_by_id(target_id):
        assert target_id == package_id
        return original

    async def fake_create_package_event(**kwargs):
        package_event_calls.append(kwargs)

    async def fake_log_package_event(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(service, "get_package_by_id", fake_get_package_by_id)
    monkeypatch.setattr(service, "_create_package_event", fake_create_package_event)
    monkeypatch.setattr("app.services.package_service.get_write_queue", lambda: _return_queue(queue))
    monkeypatch.setattr("app.services.package_service.audit_service.log_package_event", fake_log_package_event)

    with pytest.raises(ValueError, match="Failed to update package status"):
        await service.update_status(
            package_id=package_id,
            status_update=PackageStatusUpdate(status="delivered", notes="signed"),
            actor=actor,
        )

    assert len(queue.calls) == 2
    assert package_event_calls == []
    assert audit_calls == []
