# Database Schema

## Overview

Mailroom Tracking uses SQLite as an embedded application database.

- Default path: `./data/mailroom.sqlite3`
- Schema source: `app/database/schema.py`
- Bootstrap entrypoint: `app/database/migrations.py`

## Runtime Model

- Reads use thread-local SQLite connections from `app/database/connection.py`.
- Writes are serialized through `WriteQueue` in `app/database/write_queue.py`.
- Each connection enables WAL mode, foreign keys, and a 30 second busy timeout.
- The write queue runs `PRAGMA wal_checkpoint(PASSIVE)` periodically using `DATABASE_CHECKPOINT_INTERVAL`.

## Core Tables

### `users`

- `id` TEXT primary key with generated UUID-like default
- `username` unique
- `password_hash`
- `full_name`
- `role` constrained to `super_admin`, `admin`, `operator`
- `is_active`
- `must_change_password`
- `password_history`
- `failed_login_count`
- `locked_until`
- `created_at`
- `updated_at`

### `sessions`

- `id`
- `user_id` -> `users.id`
- `token` unique
- `expires_at`
- `last_activity`
- `ip_address`
- `user_agent`
- `created_at`

### `auth_events`

- `id`
- `user_id` -> `users.id` nullable
- `event_type`
- `username`
- `ip_address`
- `details`
- `created_at`

### `recipients`

- `id`
- `employee_id` unique
- `name`
- `email` unique
- `department`
- `phone`
- `location`
- `is_active`
- `created_at`
- `updated_at`

### `packages`

- `id`
- `tracking_no`
- `carrier`
- `recipient_id` -> `recipients.id`
- `status`
- `notes`
- `created_by` -> `users.id`
- `created_at`
- `updated_at`

### `package_events`

- `id`
- `package_id` -> `packages.id`
- `old_status`
- `new_status`
- `notes`
- `actor_id` -> `users.id`
- `created_at`

### `attachments`

- `id`
- `package_id` -> `packages.id`
- `filename`
- `file_path`
- `mime_type`
- `file_size`
- `uploaded_by` -> `users.id`
- `created_at`

### `system_settings`

- `key` primary key
- `value`
- `updated_by` -> `users.id` nullable
- `updated_at`

## Indexes

The schema creates indexes for the main lookup and reporting paths:

- users: username, role, active flag
- sessions: token, user_id, expires_at
- auth events: user_id, event_type, created_at
- recipients: employee_id, active flag, name, department
- packages: tracking number, recipient_id, status, created_at, created_by
- package events: package_id, actor_id, created_at
- attachments: package_id, uploaded_by

## Maintenance

Typical maintenance commands:

```python
import sqlite3

conn = sqlite3.connect("data/mailroom.sqlite3")
conn.execute("VACUUM")
conn.execute("ANALYZE")
conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
conn.close()
```

Expired sessions are cleaned up by application startup logic in `AuthService.cleanup_expired_sessions()`.
