"""Database connection management for SQLite."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from app.config import get_settings


SQLITE_TIMEOUT_SECONDS = 30.0
SQLITE_DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES


def _adapt_datetime(value: datetime) -> str:
    """Serialize datetimes consistently for SQLite storage."""
    return value.isoformat(sep=" ", timespec="microseconds")


def _convert_timestamp(raw: bytes) -> datetime:
    """Parse SQLite timestamp values back into Python datetimes."""
    value = raw.decode("utf-8")

    if value.endswith("Z"):
        value = value[:-1]

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMP", _convert_timestamp)


def create_connection(db_path: str, *, persistent: bool = False) -> sqlite3.Connection:
    """Create a SQLite connection configured for this application."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        db_file,
        timeout=SQLITE_TIMEOUT_SECONDS,
        detect_types=SQLITE_DETECT_TYPES,
        isolation_level=None,
        check_same_thread=not persistent,
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


class DatabaseConnection:
    """Manage thread-local read connections and short-lived write connections."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()

    def _get_read_connection(self) -> sqlite3.Connection:
        """Get or create the current thread's persistent connection."""
        conn = getattr(self._local, "read_connection", None)

        if conn is None:
            conn = create_connection(self.db_path, persistent=True)
            self._local.read_connection = conn

        return conn

    @contextmanager
    def get_read_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield the current thread's persistent read connection."""
        yield self._get_read_connection()

    @contextmanager
    def get_write_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a dedicated transactional write connection."""
        conn = create_connection(self.db_path)
        conn.execute("BEGIN")
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


_db_connection: DatabaseConnection | None = None


def get_db() -> DatabaseConnection:
    """Return the global database connection manager."""
    global _db_connection

    if _db_connection is None:
        _db_connection = DatabaseConnection(get_settings().database_path)

    return _db_connection


def close_db() -> None:
    """Close the global database connection manager."""
    global _db_connection

    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
