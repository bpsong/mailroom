"""Tests for user update behavior on SQLite."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models import User
from app.services.user_service import UserService


class _FakeWriteQueue:
    def __init__(self):
        self.calls: list[tuple[str, list[str]]] = []

    async def execute(self, query, params, return_result=False):
        self.calls.append((query, params))
        now = datetime.now(UTC)
        return [[
            uuid4(),
            "admin",
            "hash",
            "Admin Updated",
            "super_admin",
            True,
            False,
            None,
            0,
            None,
            now,
            now,
        ]]


async def _return_queue(queue):
    return queue


@pytest.mark.asyncio
async def test_update_user_executes_single_update_and_logs_audit(monkeypatch):
    service = UserService()
    user_id = uuid4()
    actor_id = uuid4()
    now = datetime.now(UTC)
    original = User(
        id=user_id,
        username="admin",
        password_hash="hash",
        full_name="Admin",
        role="admin",
        is_active=True,
        must_change_password=False,
        password_history=None,
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )
    actor = User(
        id=actor_id,
        username="actor",
        password_hash="hash",
        full_name="Actor",
        role="super_admin",
        is_active=True,
        must_change_password=False,
        password_history=None,
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )
    queue = _FakeWriteQueue()
    audit_calls: list[dict] = []

    async def fake_get_user_by_id(target_id):
        assert target_id == user_id
        return original

    async def fake_log_user_management(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(service, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr("app.services.user_service.get_write_queue", lambda: _return_queue(queue))
    monkeypatch.setattr("app.services.user_service.audit_service.log_user_management", fake_log_user_management)

    result = await service.update_user(
        user_id=user_id,
        full_name="Admin Updated",
        role="super_admin",
        actor=actor,
    )

    assert result.full_name == "Admin Updated"
    assert result.role == "super_admin"
    assert len(queue.calls) == 1
    assert "update users" in queue.calls[0][0].lower()
    assert audit_calls and audit_calls[0]["action"] == "user_updated"
