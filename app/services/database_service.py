"""Database service layer with retry logic and connection management."""

import asyncio
import logging
from typing import Any, Optional
from datetime import datetime

from app.database.connection import get_db
from app.database.write_queue import get_write_queue

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Database service layer providing high-level database operations.
    
    This service handles:
    - Connection pooling for read operations
    - Retry logic with exponential backoff for write operations
    - Checkpoint management
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize the database service."""
        self.db = get_db()
        self._write_queue: Optional[Any] = None
        self._retry_attempts = 3
        self._base_delay = 0.1  # 100ms base delay
    
    async def _get_write_queue(self):
        """Get or initialize the write queue."""
        if self._write_queue is None:
            self._write_queue = await get_write_queue()
        return self._write_queue
    
    async def execute_read(
        self,
        query: str,
        params: tuple | dict | None = None
    ) -> list[tuple]:
        """
        Execute a read query with connection pooling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of result tuples
        """
        try:
            with self.db.get_read_connection() as conn:
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return result.fetchall()
        except Exception as e:
            logger.error(f"Error executing read query: {e}")
            raise
    
    async def execute_read_one(
        self,
        query: str,
        params: tuple | dict | None = None
    ) -> Optional[tuple]:
        """
        Execute a read query and return a single result.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Single result tuple or None
        """
        try:
            with self.db.get_read_connection() as conn:
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return result.fetchone()
        except Exception as e:
            logger.error(f"Error executing read query: {e}")
            raise
    
    async def execute_write(
        self,
        query: str,
        params: tuple | dict | None = None,
        return_result: bool = False
    ) -> Any:
        """
        Execute a write query with retry logic and exponential backoff.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            return_result: Whether to return the query result
            
        Returns:
            Query result if return_result is True, None otherwise
        """
        write_queue = await self._get_write_queue()
        
        for attempt in range(self._retry_attempts):
            try:
                result = await write_queue.execute(
                    query=query,
                    params=params,
                    return_result=return_result
                )
                return result
            
            except Exception as e:
                if attempt < self._retry_attempts - 1:
                    # Calculate exponential backoff delay
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(
                        f"Write operation failed (attempt {attempt + 1}/{self._retry_attempts}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Write operation failed after {self._retry_attempts} attempts: {e}"
                    )
                    raise
    
    async def execute_write_many(
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
        write_queue = await self._get_write_queue()
        
        for attempt in range(self._retry_attempts):
            try:
                await write_queue.execute_many(query, params_list)
                return
            
            except Exception as e:
                if attempt < self._retry_attempts - 1:
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(
                        f"Batch write operation failed (attempt {attempt + 1}/{self._retry_attempts}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Batch write operation failed after {self._retry_attempts} attempts: {e}"
                    )
                    raise
    
    async def execute_transaction(
        self,
        operations: list[tuple[str, tuple | dict | None]]
    ) -> None:
        """
        Execute multiple operations as a transaction.
        
        Args:
            operations: List of (query, params) tuples
        """
        write_queue = await self._get_write_queue()
        
        for attempt in range(self._retry_attempts):
            try:
                # Execute all operations in sequence
                for query, params in operations:
                    await write_queue.execute(query, params)
                return
            
            except Exception as e:
                if attempt < self._retry_attempts - 1:
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(
                        f"Transaction failed (attempt {attempt + 1}/{self._retry_attempts}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Transaction failed after {self._retry_attempts} attempts: {e}"
                    )
                    raise
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            result = await self.execute_read("SELECT 1")
            return len(result) > 0 and result[0][0] == 1
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    async def get_table_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of rows in the table
        """
        try:
            result = await self.execute_read_one(
                f"SELECT COUNT(*) FROM {table_name}"
            )
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting table count for {table_name}: {e}")
            return 0
    
    def close(self) -> None:
        """Close database connections."""
        self.db.close()


# Global database service instance
_db_service: DatabaseService | None = None


def get_database_service() -> DatabaseService:
    """
    Get the global database service instance.
    
    Returns:
        DatabaseService instance
    """
    global _db_service
    
    if _db_service is None:
        _db_service = DatabaseService()
    
    return _db_service
