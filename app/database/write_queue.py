"""Async write queue for serialized SQLite write operations."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from app.config import settings
from app.database.connection import create_connection

logger = logging.getLogger(__name__)

QueryParams = tuple[Any, ...] | list[Any] | dict[str, Any] | None


@dataclass
class WriteOperation:
    """Represents a queued database write operation."""

    query: str
    params: QueryParams
    connection_callable: Optional[Callable[[Any], Any]] = None
    callback: Optional[Callable[[Any], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None
    completion_future: Optional[asyncio.Future] = None
    expects_result: bool = False
    expired: bool = False
    execution_started: bool = False

    def mark_expired(self) -> None:
        self.expired = True

    def mark_execution_started(self) -> None:
        self.execution_started = True

    def should_skip_execution(self) -> bool:
        return self.expired and not self.execution_started


class WriteQueue:
    """Serialize writes through a single async worker."""

    def __init__(self, db_path: str, checkpoint_interval: int = 300):
        self.db_path = db_path
        self.checkpoint_interval = checkpoint_interval
        self.queue: asyncio.Queue[WriteOperation] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.transaction_count = 0
        self.last_checkpoint = datetime.now()
        self.result_timeout_seconds = float(
            getattr(settings, "write_queue_result_timeout", 30.0)
        )

    async def start(self) -> None:
        """Start the worker if it is not already running."""
        self._ensure_queue_for_current_loop()

        if self.worker_task and self.worker_task.done():
            self.is_running = False
            self.worker_task = None

        if self.is_running and self.worker_task and not self.worker_task.done():
            logger.warning("Write queue worker is already running")
            return

        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Write queue worker started")

    async def stop(self) -> None:
        """Drain outstanding work and stop the worker."""
        if not self.is_running:
            return

        self.is_running = False
        await self.queue.join()

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            finally:
                self.worker_task = None

        logger.info("Write queue worker stopped")

    async def execute(
        self,
        query: str,
        params: QueryParams = None,
        return_result: bool = False,
    ) -> Any:
        """Queue a SQL write statement and wait for completion."""
        self._ensure_queue_for_current_loop()

        if (not self.is_running) or (self.worker_task and self.worker_task.done()):
            logger.warning(
                "Write queue worker not running (is_running=%s done=%s); restarting",
                self.is_running,
                self.worker_task.done() if self.worker_task else None,
            )
            await self.start()

        completion_future = asyncio.get_running_loop().create_future()
        operation = WriteOperation(
            query=query,
            params=params,
            completion_future=completion_future,
            expects_result=return_result,
        )
        await self.queue.put(operation)

        try:
            completion_value = await asyncio.wait_for(
                completion_future,
                timeout=self.result_timeout_seconds,
            )
            if return_result:
                return completion_value
            return None
        except asyncio.TimeoutError as exc:
            operation.mark_expired()
            if not completion_future.done():
                completion_future.cancel()
            logger.error(
                "WriteQueue timed out waiting for completion after %ss; query=%s; best_effort_cancel=True",
                self.result_timeout_seconds,
                " ".join(query.split())[:140],
            )
            raise TimeoutError(
                f"Timed out waiting for write queue completion after {self.result_timeout_seconds}s"
            ) from exc

    async def execute_with_connection(
        self,
        description: str,
        operation_callable: Callable[[Any], Any],
        return_result: bool = False,
    ) -> Any:
        """Run a custom transactional write callable on the worker connection."""
        self._ensure_queue_for_current_loop()

        if (not self.is_running) or (self.worker_task and self.worker_task.done()):
            logger.warning(
                "Write queue worker not running (is_running=%s done=%s); restarting",
                self.is_running,
                self.worker_task.done() if self.worker_task else None,
            )
            await self.start()

        completion_future = asyncio.get_running_loop().create_future()
        queue_operation = WriteOperation(
            query=description,
            params=None,
            connection_callable=operation_callable,
            completion_future=completion_future,
            expects_result=return_result,
        )
        await self.queue.put(queue_operation)

        try:
            completion_value = await asyncio.wait_for(
                completion_future,
                timeout=self.result_timeout_seconds,
            )
            if return_result:
                return completion_value
            return None
        except asyncio.TimeoutError as exc:
            queue_operation.mark_expired()
            if not completion_future.done():
                completion_future.cancel()
            logger.error(
                "WriteQueue timed out waiting for completion after %ss; query=%s; best_effort_cancel=True",
                self.result_timeout_seconds,
                " ".join(description.split())[:140],
            )
            raise TimeoutError(
                f"Timed out waiting for write queue completion after {self.result_timeout_seconds}s"
            ) from exc

    async def execute_many(
        self,
        query: str,
        params_list: list[tuple[Any, ...] | list[Any] | dict[str, Any]],
    ) -> None:
        """Queue multiple write operations sequentially."""
        for params in params_list:
            await self.execute(query=query, params=params, return_result=False)

    def _ensure_queue_for_current_loop(self) -> None:
        """Rebind the queue if the active event loop changes."""
        current_loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = current_loop
            return

        if self._loop is current_loop:
            return

        old_queue = self.queue
        self.queue = asyncio.Queue()
        moved = 0
        while True:
            try:
                self.queue.put_nowait(old_queue.get_nowait())
                moved += 1
            except asyncio.QueueEmpty:
                break

        logger.warning(
            "Write queue event loop changed; rebound queue from %s to %s (moved_ops=%s)",
            id(self._loop),
            id(current_loop),
            moved,
        )
        self._loop = current_loop

    def _resolve_future_success(self, future: asyncio.Future, value: Any) -> None:
        """Safely resolve the queued operation future."""
        try:
            if not future.done() and not future.cancelled():
                future.set_result(value)
        except Exception as exc:
            logger.warning("Failed setting write queue result future: %s", exc)

    def _resolve_future_error(self, future: asyncio.Future, exc: Exception) -> None:
        """Safely resolve the queued operation future with an error."""
        try:
            if not future.done() and not future.cancelled():
                future.set_exception(exc)
        except Exception as set_exc:
            logger.warning("Failed setting write queue exception future: %s", set_exc)

    async def _worker(self) -> None:
        """Process queued write operations."""
        conn = create_connection(self.db_path)

        try:
            while self.is_running:
                try:
                    operation = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    normalized_query = " ".join(operation.query.split())
                    params_repr = repr(operation.params)
                    op_fingerprint = hashlib.sha256(
                        f"{normalized_query}|{params_repr}".encode("utf-8")
                    ).hexdigest()[:12]

                    try:
                        if operation.should_skip_execution():
                            logger.warning(
                                "Skipping expired write operation op=%s query=%s",
                                op_fingerprint,
                                normalized_query[:140],
                            )
                            if operation.completion_future:
                                self._resolve_future_error(
                                    operation.completion_future,
                                    TimeoutError("Write operation expired before execution started"),
                                )
                            continue

                        operation.mark_execution_started()
                        conn.execute("BEGIN")

                        if operation.connection_callable is not None:
                            raw_result = operation.connection_callable(conn)
                        elif operation.params is not None:
                            raw_result = conn.execute(operation.query, operation.params)
                        else:
                            raw_result = conn.execute(operation.query)

                        completion_value = None
                        if operation.expects_result:
                            if hasattr(raw_result, "fetchall"):
                                completion_value = raw_result.fetchall()
                            else:
                                completion_value = raw_result

                        conn.commit()
                        self.transaction_count += 1

                        if operation.completion_future:
                            self._resolve_future_success(
                                operation.completion_future,
                                completion_value,
                            )

                        if operation.callback:
                            operation.callback(raw_result)

                    except Exception as exc:
                        logger.error(
                            "Error executing write operation op=%s query=%s params=%s error=%s",
                            op_fingerprint,
                            normalized_query[:140],
                            params_repr,
                            exc,
                        )
                        try:
                            conn.rollback()
                        except Exception as rollback_error:
                            logger.warning(
                                "Rollback skipped/failed op=%s reason=%s",
                                op_fingerprint,
                                rollback_error,
                            )

                        if operation.completion_future:
                            self._resolve_future_error(operation.completion_future, exc)

                        if operation.error_callback:
                            operation.error_callback(exc)

                    finally:
                        self.queue.task_done()

                    await self._check_checkpoint(conn)

                except asyncio.TimeoutError:
                    await self._check_checkpoint(conn)
                    continue

        finally:
            self.is_running = False
            conn.close()

    async def _check_checkpoint(self, conn) -> None:
        """Checkpoint the SQLite WAL periodically."""
        now = datetime.now()
        time_since_checkpoint = (now - self.last_checkpoint).total_seconds()

        if self.transaction_count >= 1000 or time_since_checkpoint >= self.checkpoint_interval:
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                self.transaction_count = 0
                self.last_checkpoint = now
                logger.debug("Database checkpoint completed")
            except Exception as exc:
                logger.error("Error during checkpoint: %s", exc)


_write_queue: WriteQueue | None = None


async def get_write_queue() -> WriteQueue:
    """Return the global write queue instance."""
    global _write_queue

    if _write_queue is None:
        _write_queue = WriteQueue(
            settings.database_path,
            settings.database_checkpoint_interval,
        )
        await _write_queue.start()

    return _write_queue


async def close_write_queue() -> None:
    """Close the global write queue instance."""
    global _write_queue

    if _write_queue is not None:
        await _write_queue.stop()
        _write_queue = None
