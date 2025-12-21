"""Database connection management with connection pooling."""

import duckdb
from contextlib import contextmanager
from typing import Generator

from app.config import settings


class DatabaseConnection:
    """
    Database connection manager with connection pooling for reads.
    
    This class manages DuckDB connections with WAL mode enabled for better
    concurrency. It provides separate connections for read and write operations.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database connection manager.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
    
    def _get_read_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get a fresh read connection.
        
        Returns:
            DuckDB connection for read operations
        """
        return duckdb.connect(self.db_path, read_only=False)
    
    @contextmanager
    def get_read_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager for read connections.
        
        Yields:
            DuckDB connection for read operations
        """
        conn = self._get_read_connection()
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def get_write_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager for write connections.
        
        Note: Write operations should go through the WriteQueue to prevent locking.
        This method is provided for migration scripts and administrative tasks.
        
        Yields:
            DuckDB connection for write operations
        """
        conn = duckdb.connect(self.db_path, read_only=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def close(self) -> None:
        """Close resources (no-op for read connections)."""
        pass


# Global database connection instance
_db_connection: DatabaseConnection | None = None


def get_db() -> DatabaseConnection:
    """
    Get the global database connection instance.
    
    Returns:
        DatabaseConnection instance
    """
    global _db_connection
    
    if _db_connection is None:
        _db_connection = DatabaseConnection(settings.database_path)
    
    return _db_connection


def close_db() -> None:
    """Close the global database connection."""
    global _db_connection
    
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
