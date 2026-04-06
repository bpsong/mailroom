"""Async write queue to prevent database locking issues."""

import asyncio
import duckdb
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)

QueryParams = tuple[Any, ...] | list[Any] | dict[str, Any] | None


@dataclass
class WriteOperation:
    """Represents a database write operation."""
    
    query: str
    params: QueryParams
    callback: Optional[Callable[[Any], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None
    result_future: Optional[asyncio.Future] = None
    expired: bool = False
    execution_started: bool = False

    def mark_expired(self) -> None:
        """Mark the operation as expired for best-effort cancellation."""
        self.expired = True

    def mark_execution_started(self) -> None:
        """Mark the operation as having started database execution."""
        self.execution_started = True

    def should_skip_execution(self) -> bool:
        """Return True when an expired operation can still be skipped safely."""
        return self.expired and not self.execution_started


class WriteQueue:
    """
    Async write queue for DuckDB operations.
    
    This queue ensures all write operations go through a single worker task,
    preventing database locking issues that can occur with concurrent writes.
    """
    
    def __init__(self, db_path: str, checkpoint_interval: int = 300):
        """
        Initialize the write queue.
        
        Args:
            db_path: Path to the DuckDB database file
            checkpoint_interval: Seconds between checkpoints (default: 300)
        """
        self.db_path = db_path
        self.checkpoint_interval = checkpoint_interval
        self.queue: asyncio.Queue[WriteOperation] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.transaction_count = 0
        self.last_checkpoint = datetime.now()
        # Maximum seconds callers wait for return_result=True operations.
        # Prevents request handlers from hanging forever if worker fails.
        self.result_timeout_seconds = float(
            getattr(settings, "write_queue_result_timeout", 30.0)
        )
    
    async def start(self) -> None:
        """Start the write queue worker."""
        self._ensure_queue_for_current_loop()

        if self.worker_task and self.worker_task.done():
            # Worker task ended (possibly due to event-loop shutdown/crash).
            # Reset running state so we can start a fresh worker.
            self.is_running = False
            self.worker_task = None

        if self.is_running and self.worker_task and not self.worker_task.done():
            logger.warning("Write queue worker is already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Write queue worker started")
    
    async def stop(self) -> None:
        """Stop the write queue worker and wait for pending operations."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for queue to be empty
        await self.queue.join()
        
        # Cancel worker task
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
        return_result: bool = False
    ) -> Any:
        """
        Execute a write operation through the queue.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            return_result: Whether to return the query result
            
        Returns:
            Query result if return_result is True, None otherwise

        Raises:
            TimeoutError: Raised only for the *caller wait window* when
                `return_result=True` and the result future is not resolved
                within `self.result_timeout_seconds`.

        Notes:
            Timeout uses best-effort cancellation semantics. If the worker has
            not started database execution when the caller wait window expires,
            the queued operation is skipped. If execution already started,
            the write may still commit later even though the caller receives a
            timeout.
        """
        self._ensure_queue_for_current_loop()

        # Self-heal if worker stopped/crashed so writes don't queue indefinitely.
        if (not self.is_running) or (self.worker_task and self.worker_task.done()):
            logger.warning(
                "Write queue worker not running (is_running=%s done=%s); restarting",
                self.is_running,
                self.worker_task.done() if self.worker_task else None,
            )
            await self.start()

        if return_result:
            future = asyncio.get_running_loop().create_future()
            operation = WriteOperation(
                query=query,
                params=params,
                result_future=future
            )
            await self.queue.put(operation)
            try:
                return await asyncio.wait_for(future, timeout=self.result_timeout_seconds)
            except asyncio.TimeoutError as exc:
                operation.mark_expired()
                if not future.done():
                    future.cancel()
                logger.error(
                    "WriteQueue timed out waiting for result after %ss; query=%s; best_effort_cancel=True",
                    self.result_timeout_seconds,
                    " ".join(query.split())[:140],
                )
                raise TimeoutError(
                    f"Timed out waiting for write queue result after {self.result_timeout_seconds}s"
                ) from exc
        else:
            operation = WriteOperation(query=query, params=params)
            await self.queue.put(operation)
            return None

    def _ensure_queue_for_current_loop(self) -> None:
        """Ensure the internal queue is bound to the active event loop."""
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
        """Safely resolve operation future with a result."""
        try:
            if not future.done() and not future.cancelled():
                future.set_result(value)
        except Exception as exc:
            logger.warning("Failed setting write queue result future: %s", exc)

    def _resolve_future_error(self, future: asyncio.Future, exc: Exception) -> None:
        """Safely resolve operation future with an exception."""
        try:
            if not future.done() and not future.cancelled():
                future.set_exception(exc)
        except Exception as set_exc:
            logger.warning("Failed setting write queue exception future: %s", set_exc)
    
    async def execute_many(
        self,
        query: str,
        params_list: list[tuple[Any, ...] | list[Any] | dict[str, Any]]
    ) -> None:
        """
        Execute multiple write operations with the same query.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter sets
        """
        for params in params_list:
            operation = WriteOperation(query=query, params=params)
            await self.queue.put(operation)
    
    async def _worker(self) -> None:
        """Worker task that processes write operations."""
        conn = duckdb.connect(self.db_path, read_only=False)
        
        try:
            while self.is_running:
                try:
                    # Get operation with timeout to allow periodic checks
                    operation = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                    op_started_at = datetime.now().isoformat(timespec="milliseconds")
                    normalized_query = " ".join(operation.query.split())
                    params_repr = repr(operation.params)
                    op_fingerprint = hashlib.sha256(
                        f"{normalized_query}|{params_repr}".encode("utf-8")
                    ).hexdigest()[:12]
                    logger.debug(
                        "WriteQueue start op=%s ts=%s queue_depth_after_get=%s query=%s params_hash=%s",
                        op_fingerprint,
                        op_started_at,
                        self.queue.qsize(),
                        normalized_query[:140],
                        hashlib.sha256(params_repr.encode("utf-8")).hexdigest()[:12],
                    )
                    
                    try:
                        if operation.should_skip_execution():
                            logger.warning(
                                "Skipping expired write operation op=%s query=%s",
                                op_fingerprint,
                                normalized_query[:140],
                            )
                            continue

                        operation.mark_execution_started()

                        # Execute the operation
                        if operation.params:
                            result = conn.execute(operation.query, operation.params)
                        else:
                            result = conn.execute(operation.query)
                        
                        # Commit the transaction
                        conn.commit()
                        
                        # Increment transaction counter
                        self.transaction_count += 1
                        
                        # Return result if requested
                        if operation.result_future:
                            try:
                                # Fetch result before setting future
                                fetched_result = result.fetchall() if result else None
                                self._resolve_future_success(operation.result_future, fetched_result)
                            except Exception as e:
                                self._resolve_future_error(operation.result_future, e)
                        
                        # Call success callback if provided
                        if operation.callback:
                            operation.callback(result)

                        logger.debug(
                            "WriteQueue success op=%s queue_depth_after_execute=%s",
                            op_fingerprint,
                            self.queue.qsize(),
                        )
                        
                    except Exception as e:
                        logger.error(
                            "Error executing write operation op=%s query=%s params=%s error=%s",
                            op_fingerprint,
                            normalized_query[:140],
                            params_repr,
                            e,
                        )
                        conn.rollback()
                        
                        # Set exception on future if provided
                        if operation.result_future:
                            self._resolve_future_error(operation.result_future, e)
                        
                        # Call error callback if provided
                        if operation.error_callback:
                            operation.error_callback(e)
                    
                    finally:
                        self.queue.task_done()
                    
                    # Check if checkpoint is needed
                    await self._check_checkpoint(conn)
                
                except asyncio.TimeoutError:
                    # No operation received, check checkpoint anyway
                    await self._check_checkpoint(conn)
                    continue
        
        finally:
            self.is_running = False
            conn.close()
    
    async def _check_checkpoint(self, conn: duckdb.DuckDBPyConnection) -> None:
        """
        Check if a checkpoint is needed and perform it.
        
        Args:
            conn: DuckDB connection
        """
        now = datetime.now()
        time_since_checkpoint = (now - self.last_checkpoint).total_seconds()
        
        # Checkpoint every 1000 transactions or checkpoint_interval seconds
        if self.transaction_count >= 1000 or time_since_checkpoint >= self.checkpoint_interval:
            try:
                conn.execute("CHECKPOINT")
                self.transaction_count = 0
                self.last_checkpoint = now
                logger.debug("Database checkpoint completed")
            except Exception as e:
                logger.error(f"Error during checkpoint: {e}")


# Global write queue instance
_write_queue: WriteQueue | None = None


async def get_write_queue() -> WriteQueue:
    """
    Get the global write queue instance.
    
    Returns:
        WriteQueue instance
    """
    global _write_queue
    
    if _write_queue is None:
        _write_queue = WriteQueue(
            settings.database_path,
            settings.database_checkpoint_interval
        )
        await _write_queue.start()
    
    return _write_queue


async def close_write_queue() -> None:
    """Close the global write queue."""
    global _write_queue
    
    if _write_queue is not None:
        await _write_queue.stop()
        _write_queue = None
