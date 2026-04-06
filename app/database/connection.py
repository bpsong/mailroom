"""Database connection management with thread-local read connection reuse."""

import threading
import duckdb
from contextlib import contextmanager
from typing import Generator

from app.config import get_settings


class DatabaseConnection:
    """
    Database connection manager with thread-local read connection reuse.
    
    This class manages DuckDB connections with WAL mode enabled for better
    concurrency. It provides reusable per-thread read connections and dedicated
    write connections for write operations.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database connection manager.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self._local = threading.local()
    
    def _get_read_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get or create the current thread's persistent read connection.
        
        Returns:
            DuckDB connection for read operations
        """
        conn = getattr(self._local, "read_connection", None)

        if conn is None:
            conn = duckdb.connect(self.db_path, read_only=False)
            self._local.read_connection = conn

        return conn
    
    @contextmanager
    def get_read_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager for the current thread's read connection.
        
        Yields:
            DuckDB connection for read operations
        """
        yield self._get_read_connection()
    
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
        """Close the current thread's persistent read connection, if present."""
        conn = getattr(self._local, "read_connection", None)

        if conn is not None:
            conn.close()
            self._local.read_connection = None


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
        _db_connection = DatabaseConnection(get_settings().database_path)
    
    return _db_connection


def close_db() -> None:
    """Close the global database connection."""
    global _db_connection
    
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
