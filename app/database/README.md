# Database Module

This module provides the Mailroom Tracking database layer on top of SQLite.

## Components

### `schema.py`

- Defines the SQLite schema and indexes.
- Creates all required tables, including `system_settings`.
- Verifies table presence during bootstrap.

### `connection.py`

- Builds SQLite connections with WAL mode and foreign keys enabled.
- Reuses one read connection per thread.
- Exposes short-lived transactional write connections for administrative work.

### `write_queue.py`

- Serializes writes through a single async worker.
- Preserves caller timeout semantics for queued writes.
- Periodically checkpoints the WAL.

### `migrations.py`

- Initializes the SQLite schema.
- Bootstraps the first super admin account.
- Resets the database by deleting the SQLite file set and recreating it.

## Configuration

```env
DATABASE_PATH=./data/mailroom.sqlite3
DATABASE_CHECKPOINT_INTERVAL=300
```

## Operational Notes

- SQLite is embedded; no external database server is required.
- The application still uses a write queue to keep concurrent writes predictable.
- Foreign keys are enabled across the schema.
