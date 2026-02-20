# Database Schema Documentation

## Overview

Mailroom Tracking uses DuckDB with an async write queue for serialized writes.

- Default DB path: `./data/mailroom.duckdb`
- Base schema source: `app/database/schema.py`
- Startup migration entry: `app/database/migrations.py`

## Concurrency Model

- Writes are funneled through `WriteQueue` (`app/database/write_queue.py`)
- Reads use fresh connections from `DatabaseConnection.get_read_connection()`
- Checkpoints run every 1000 write transactions or `DATABASE_CHECKPOINT_INTERVAL` seconds

## Core Tables (Base Schema)

### `users`

Columns:
- `id` UUID PK
- `username` VARCHAR NOT NULL UNIQUE
- `password_hash` VARCHAR NOT NULL
- `full_name` VARCHAR NOT NULL
- `role` VARCHAR CHECK (`super_admin`, `admin`, `operator`)
- `is_active` BOOLEAN DEFAULT true
- `must_change_password` BOOLEAN DEFAULT false
- `password_history` TEXT (JSON)
- `failed_login_count` INTEGER DEFAULT 0
- `locked_until` TIMESTAMP NULL
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

Indexes:
- `idx_users_username`, `idx_users_role`, `idx_users_is_active`

### `sessions`

Columns:
- `id` UUID PK
- `user_id` UUID NOT NULL FK -> `users(id)`
- `token` VARCHAR NOT NULL UNIQUE
- `expires_at` TIMESTAMP NOT NULL
- `last_activity` TIMESTAMP
- `ip_address` VARCHAR NULL
- `user_agent` TEXT NULL
- `created_at` TIMESTAMP

Indexes:
- `idx_sessions_token`, `idx_sessions_user_id`, `idx_sessions_expires_at`

### `auth_events`

Columns:
- `id` UUID PK
- `user_id` UUID NULL FK -> `users(id)`
- `event_type` VARCHAR NOT NULL
- `username` VARCHAR NULL
- `ip_address` VARCHAR NULL
- `details` TEXT NULL (JSON)
- `created_at` TIMESTAMP

Indexes:
- `idx_auth_events_user_id`, `idx_auth_events_event_type`, `idx_auth_events_created_at`

### `recipients`

Columns:
- `id` UUID PK
- `employee_id` VARCHAR NOT NULL UNIQUE
- `name` VARCHAR NOT NULL
- `email` VARCHAR NOT NULL UNIQUE
- `department` VARCHAR NULL in DB (app-level logic enforces non-empty on create/update)
- `phone` VARCHAR NULL
- `location` VARCHAR NULL
- `is_active` BOOLEAN DEFAULT true
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

Indexes:
- `idx_recipients_employee_id`, `idx_recipients_is_active`, `idx_recipients_name`, `idx_recipients_department`

### `packages`

Columns:
- `id` UUID PK
- `tracking_no` VARCHAR NOT NULL
- `carrier` VARCHAR NOT NULL
- `recipient_id` UUID NOT NULL FK -> `recipients(id)`
- `status` VARCHAR CHECK (`registered`, `awaiting_pickup`, `out_for_delivery`, `delivered`, `returned`)
- `notes` TEXT NULL
- `created_by` UUID NOT NULL FK -> `users(id)`
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

Indexes:
- `idx_packages_tracking_no`, `idx_packages_recipient_id`, `idx_packages_status`, `idx_packages_created_at`, `idx_packages_created_by`

### `package_events`

Columns:
- `id` UUID PK
- `package_id` UUID NOT NULL
- `old_status` VARCHAR NULL
- `new_status` VARCHAR NOT NULL
- `notes` TEXT NULL
- `actor_id` UUID NOT NULL
- `created_at` TIMESTAMP

Important note:
- In current base schema, `package_events` has no foreign keys (DuckDB update/workflow constraints noted in source comments).

Indexes:
- `idx_package_events_package_id`, `idx_package_events_actor_id`, `idx_package_events_created_at`

### `attachments`

Columns:
- `id` UUID PK
- `package_id` UUID NOT NULL
- `filename` VARCHAR NOT NULL
- `file_path` VARCHAR NOT NULL
- `mime_type` VARCHAR NOT NULL
- `file_size` INTEGER NOT NULL
- `uploaded_by` UUID NOT NULL
- `created_at` TIMESTAMP

Important note:
- In current base schema, `attachments` has no foreign keys (same rationale as above).

Indexes:
- `idx_attachments_package_id`, `idx_attachments_uploaded_by`

## `system_settings` Table Status

`system_settings` is used by QR base URL features (`app/services/system_settings_service.py`) but is **not** part of the base schema in `app/database/schema.py`.

It is created by standalone migration scripts under `app/database/migrations/`:
- `create_system_settings_table.py`
- `fix_system_settings_fk.py`
- `simplify_system_settings.py`

Current service behavior:
- Reads gracefully handle missing table (`get_qr_base_url()` returns `None`)
- Writes require table existence (`set_qr_base_url()` inserts/updates `system_settings`)

## Operational Notes

- Startup runs `run_initial_migration(create_super_admin=True)`.
- Initial super admin defaults: username `admin`, password `ChangeMe123!` (forced password change on first login).
- Recipient department backfill enforcement runs on migration manager startup (`_enforce_recipient_department_requirement`).

## Maintenance

Common maintenance SQL:
```sql
VACUUM;
ANALYZE;
CHECKPOINT;
```

Session cleanup logic is implemented in app services, and expired sessions are cleaned during startup.
