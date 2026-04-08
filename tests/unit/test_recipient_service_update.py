"""Tests for recipient update behavior."""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.models import Recipient, RecipientUpdate
from app.services.recipient_service import RecipientService


class _FakeWriteQueue:
    def __init__(self, fail_first: bool = False):
        self.fail_first = fail_first
        self.calls: list[tuple[str, list[str | None]]] = []

    async def execute(self, query, params, return_result=False):
        self.calls.append((query, params))
        if self.fail_first:
            self.fail_first = False
            raise Exception('Constraint Error: Duplicate key "id: abc" violates primary key constraint')
        return None


@pytest.mark.asyncio
async def test_update_recipient_retries_with_merge_on_duplicate_key(monkeypatch):
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
    queue = _FakeWriteQueue(fail_first=True)

    async def fake_get_recipient_by_id(target_id):
        assert target_id == recipient_id
        if len(queue.calls) >= 2:
            return updated
        return original

    monkeypatch.setattr(service, "get_recipient_by_id", fake_get_recipient_by_id)
    monkeypatch.setattr(service, "_email_exists", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.services.recipient_service.get_write_queue", lambda: queue)

    result = await service.update_recipient(
        recipient_id=recipient_id,
        recipient_data=RecipientUpdate(name="Updated Name"),
    )

    assert result.name == "Updated Name"
    assert len(queue.calls) == 2
    assert "update recipients" in queue.calls[0][0].lower()
    assert "merge into recipients" in queue.calls[1][0].lower()


@pytest.mark.asyncio
async def test_duplicate_id_error_matcher_is_specific():
    assert RecipientService._is_duplicate_id_update_error(
        Exception('Constraint Error: Duplicate key "id: abc" violates primary key constraint')
    )
    assert not RecipientService._is_duplicate_id_update_error(Exception("some other database error"))
