"""Async write queue to prevent database locking issues."""

import asyncio
import duckdb
from dataclasses import dataclass
from typing import Any, Callable, Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WriteOperation:
    """Represents a database write operation."""
    
    query: str
    params: tuple | dict | None
    callback: Optional[Callable[[Any], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None
    result_future: Optional[asyncio.Future] = None


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
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.transaction_count = 0
        self.last_checkpoint = datetime.now()
    
    async def start(self) -> None:
        """Start the write queue worker."""
        if self.is_running:
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
        
        logger.info("Write queue worker stopped")
    
    async def execute(
        self,
        query: str,
        params: tuple | dict | None = None,
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
        """
        if return_result:
            future = asyncio.get_event_loop().create_future()
            operation = WriteOperation(
                query=query,
                params=params,
                result_future=future
            )
            await self.queue.put(operation)
            return await future
        else:
            operation = WriteOperation(query=query, params=params)
            await self.queue.put(operation)
            return None
    
    async def execute_many(
        self,
        query: str,
        params_list: list[tuple | dict]
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
                    
                    try:
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
                                operation.result_future.set_result(fetched_result)
                            except Exception as e:
                                operation.result_future.set_exception(e)
                        
                        # Call success callback if provided
                        if operation.callback:
                            operation.callback(result)
                        
                    except Exception as e:
                        logger.error(f"Error executing write operation: {e}")
                        conn.rollback()
                        
                        # Set exception on future if provided
                        if operation.result_future:
                            operation.result_future.set_exception(e)
                        
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
