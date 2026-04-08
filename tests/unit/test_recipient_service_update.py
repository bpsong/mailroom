"""Tests for recipient update behavior on SQLite."""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.models import Recipient, RecipientUpdate
from app.services.recipient_service import RecipientService


class _FakeWriteQueue:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple[str, list[str | None]]] = []

    async def execute(self, query, params, return_result=False):
        self.calls.append((query, params))
        if self.fail:
            raise Exception("database unavailable")
        return None


async def _async_false(*args, **kwargs):
    return False


async def _return_queue(queue):
    return queue


@pytest.mark.asyncio
async def test_update_recipient_uses_single_update_query(monkeypatch):
    service = RecipientService()
    recipient_id = uuid4()
    now = datetime.now(UTC)
    original = Recipient(
        id=recipient_id,
        employee_id="EMP1001",
        name="Original Name",
        email="original@example.com",
        department="Operations",
        phone="555-0101",
        location="Floor 1",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    updated = original.model_copy(update={"name": "Updated Name"})
    queue = _FakeWriteQueue()

    async def fake_get_recipient_by_id(target_id):
        assert target_id == recipient_id
        if queue.calls:
            return updated
        return original

    monkeypatch.setattr(service, "get_recipient_by_id", fake_get_recipient_by_id)
    monkeypatch.setattr(service, "_email_exists", _async_false)
    monkeypatch.setattr("app.services.recipient_service.get_write_queue", lambda: _return_queue(queue))

    result = await service.update_recipient(
        recipient_id=recipient_id,
        recipient_data=RecipientUpdate(
            name="Updated Name",
            email=None,
            department=None,
            phone=None,
            location=None,
        ),
    )

    assert result.name == "Updated Name"
    assert len(queue.calls) == 1
    assert "update recipients" in queue.calls[0][0].lower()


@pytest.mark.asyncio
async def test_update_recipient_raises_original_error_on_write_failure(monkeypatch):
    service = RecipientService()
    recipient_id = uuid4()
    now = datetime.now(UTC)
    original = Recipient(
        id=recipient_id,
        employee_id="EMP1002",
        name="Original Name",
        email="original2@example.com",
        department="Ops",
        phone="555-0102",
        location="Floor 2",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    queue = _FakeWriteQueue(fail=True)

    async def fake_get_recipient_by_id(target_id):
        assert target_id == recipient_id
        return original

    monkeypatch.setattr(service, "get_recipient_by_id", fake_get_recipient_by_id)
    monkeypatch.setattr(service, "_email_exists", _async_false)
    monkeypatch.setattr("app.services.recipient_service.get_write_queue", lambda: _return_queue(queue))

    with pytest.raises(Exception, match="database unavailable"):
        await service.update_recipient(
            recipient_id=recipient_id,
            recipient_data=RecipientUpdate(
                name="Updated Name",
                email=None,
                department=None,
                phone=None,
                location=None,
            ),
        )
