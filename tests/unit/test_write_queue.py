"""Unit tests for write queue timeout semantics."""

import asyncio
from typing import cast

import pytest

from app.database.write_queue import WriteOperation, WriteQueue


@pytest.mark.asyncio
async def test_timeout_skips_operation_when_execution_has_not_started():
    """Timed-out operations are skipped when the worker has not started execution."""
    queue = WriteQueue("test_mailroom.db")
    queue.result_timeout_seconds = 0.01
    captured: dict[str, WriteOperation] = {}

    async def fake_worker() -> None:
        operation = await queue.queue.get()
        captured["operation"] = operation
        await asyncio.sleep(0.03)

        assert operation.should_skip_execution() is True

        queue.queue.task_done()

    async def fake_start() -> None:
        queue.is_running = True
        queue.worker_task = asyncio.create_task(fake_worker())

    queue.start = fake_start  # type: ignore[method-assign]

    with pytest.raises(TimeoutError):
        await queue.execute("INSERT INTO users VALUES (1)", return_result=True)

    assert queue.worker_task is not None
    await queue.worker_task

    operation = captured["operation"]
    assert operation.completion_future is not None
    assert operation.expired is True
    assert operation.execution_started is False
    assert operation.completion_future.cancelled() is True


@pytest.mark.asyncio
async def test_timeout_does_not_interrupt_in_flight_operation_completion():
    """Timed-out operations may still finish after execution has started."""
    queue = WriteQueue("test_mailroom.db")
    queue.result_timeout_seconds = 0.01
    captured: dict[str, WriteOperation] = {}
    execution_state = {"completed": False}

    async def fake_worker() -> None:
        operation = await queue.queue.get()
        captured["operation"] = operation
        operation.mark_execution_started()

        await asyncio.sleep(0.03)

        execution_state["completed"] = True
        assert operation.completion_future is not None
        queue._resolve_future_success(operation.completion_future, [("done",)])
        queue.queue.task_done()

    async def fake_start() -> None:
        queue.is_running = True
        queue.worker_task = asyncio.create_task(fake_worker())

    queue.start = fake_start  # type: ignore[method-assign]

    with pytest.raises(TimeoutError):
        await queue.execute("INSERT INTO users VALUES (1)", return_result=True)

    assert queue.worker_task is not None
    await queue.worker_task

    operation = cast(WriteOperation, captured["operation"])
    assert operation.completion_future is not None
    assert operation.expired is True
    assert operation.execution_started is True
    assert execution_state["completed"] is True
    assert operation.completion_future.cancelled() is True


@pytest.mark.asyncio
async def test_non_result_write_failure_is_raised_to_caller():
    """Non-result writes should still propagate worker failures back to the caller."""
    queue = WriteQueue("test_mailroom.db")
    captured: dict[str, WriteOperation] = {}

    async def fake_worker() -> None:
        operation = await queue.queue.get()
        captured["operation"] = operation
        operation.mark_execution_started()
        assert operation.completion_future is not None
        queue._resolve_future_error(operation.completion_future, RuntimeError("boom"))
        queue.queue.task_done()

    async def fake_start() -> None:
        queue.is_running = True
        queue.worker_task = asyncio.create_task(fake_worker())

    queue.start = fake_start  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="boom"):
        await queue.execute("UPDATE users SET username = 'x'", return_result=False)

    assert queue.worker_task is not None
    await queue.worker_task

    operation = captured["operation"]
    assert operation.completion_future is not None
    assert operation.completion_future.done() is True


@pytest.mark.asyncio
async def test_execute_with_connection_returns_custom_result():
    """Custom connection operations should return fetched results to the caller."""
    queue = WriteQueue("test_mailroom.db")
    captured: dict[str, WriteOperation] = {}

    async def fake_worker() -> None:
        operation = await queue.queue.get()
        captured["operation"] = operation
        operation.mark_execution_started()
        assert operation.connection_callable is not None
        assert operation.completion_future is not None
        queue._resolve_future_success(operation.completion_future, [("ok",)])
        queue.queue.task_done()

    async def fake_start() -> None:
        queue.is_running = True
        queue.worker_task = asyncio.create_task(fake_worker())

    queue.start = fake_start  # type: ignore[method-assign]

    result = await queue.execute_with_connection(
        description="custom-op",
        operation_callable=lambda conn: None,
        return_result=True,
    )

    assert result == [("ok",)]
    assert queue.worker_task is not None
    await queue.worker_task
    assert captured["operation"].expects_result is True
