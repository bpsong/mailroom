# Database Module

This module provides the database layer for the Mailroom Tracking System using DuckDB.

## Components

### Schema (`schema.py`)
- Defines all database tables and indexes
- Provides `init_database()` function to create schema
- Provides `verify_schema()` function to check if all tables exist

### Connection (`connection.py`)
- `DatabaseConnection`: Manages thread-local read connections
- `get_db()`: Returns the global database connection instance
- Provides context managers for read and write operations

### Write Queue (`write_queue.py`)
- `WriteQueue`: Async queue for write operations to prevent locking
- Implements retry logic with exponential backoff
- Performs automatic checkpoints every 1000 transactions or 5 minutes
- `get_write_queue()`: Returns the global write queue instance

### Migrations (`migrations.py`)
- `MigrationManager`: Handles database initialization and migrations
- `run_initial_migration()`: Runs initial setup and creates super admin
- `bootstrap_super_admin()`: Creates the first super admin user

## Database Schema

The database includes the following tables:

- **users**: User accounts with authentication details
- **sessions**: Active user sessions
- **auth_events**: Authentication audit log
- **recipients**: Package recipients (employees)
- **packages**: Package tracking records
- **package_events**: Package status change history
- **attachments**: Package photos and files

## Usage

### Initialize Database

```bash
# Using the migration script
python scripts/migrate.py init

# With custom super admin credentials
python scripts/migrate.py init --username myadmin --password MySecurePass123!

# Without creating super admin
python scripts/migrate.py init --no-super-admin
```

### Verify Schema

```bash
python scripts/migrate.py verify
```

### Reset Database (WARNING: Deletes all data)

```bash
python scripts/migrate.py reset --confirm
```

### In Application Code

```python
from app.services.database_service import get_database_service

# Get database service
db_service = get_database_service()

# Read operations
results = await db_service.execute_read(
    "SELECT * FROM users WHERE username = ?",
    (username,)
)

# Write operations (with retry logic)
await db_service.execute_write(
    "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
    (username, password_hash, full_name, role)
)

# Batch operations
await db_service.execute_write_many(
    "INSERT INTO recipients (employee_id, name, email) VALUES (?, ?, ?)",
    [(emp_id1, name1, email1), (emp_id2, name2, email2)]
)
```

## Features

### Connection Pooling
- Thread-local read connections for better performance
- Separate write queue to prevent database locking

### Retry Logic
- Automatic retry with exponential backoff for write operations
- Default: 3 attempts with delays of 100ms, 200ms, 400ms

### Checkpointing
- Automatic checkpoints every 1000 transactions
- Time-based checkpoints every 5 minutes (configurable)

### Error Handling
- Comprehensive error logging
- Transaction rollback on failures
- Connection cleanup on shutdown

## Configuration

Database settings are configured in `.env`:

```env
DATABASE_PATH=./data/mailroom.duckdb
DATABASE_CHECKPOINT_INTERVAL=300  # seconds
```

## Notes

- DuckDB is an embedded database (single file)
- All write operations go through the async write queue
- Read operations use connection pooling for better performance
- The database file is created automatically on first run
- Foreign key constraints are enforced but CASCADE is not supported
