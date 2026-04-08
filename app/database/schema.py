"""Database schema definitions and initialization."""

from __future__ import annotations

from pathlib import Path

from app.database.connection import create_connection


UUID_DEFAULT_SQL = (
    "("
    "lower(hex(randomblob(4))) || '-' || "
    "lower(hex(randomblob(2))) || '-' || "
    "'4' || substr(lower(hex(randomblob(2))), 2) || '-' || "
    "substr('89ab', 1 + (abs(random()) % 4), 1) || substr(lower(hex(randomblob(2))), 2) || '-' || "
    "lower(hex(randomblob(6)))"
    ")"
)


SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin', 'operator')),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    must_change_password BOOLEAN NOT NULL DEFAULT 0,
    password_history TEXT,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    user_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS auth_events (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    user_id TEXT,
    event_type TEXT NOT NULL,
    username TEXT,
    ip_address TEXT,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS recipients (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    employee_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department TEXT,
    phone TEXT,
    location TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS packages (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    tracking_no TEXT NOT NULL,
    carrier TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('registered', 'awaiting_pickup', 'out_for_delivery', 'delivered', 'returned')),
    notes TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipient_id) REFERENCES recipients(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS package_events (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    package_id TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    notes TEXT,
    actor_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (package_id) REFERENCES packages(id),
    FOREIGN KEY (actor_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY NOT NULL DEFAULT {UUID_DEFAULT_SQL},
    package_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (package_id) REFERENCES packages(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_by TEXT,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_events_user_id ON auth_events(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_events_event_type ON auth_events(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_events_created_at ON auth_events(created_at);

CREATE INDEX IF NOT EXISTS idx_recipients_employee_id ON recipients(employee_id);
CREATE INDEX IF NOT EXISTS idx_recipients_is_active ON recipients(is_active);
CREATE INDEX IF NOT EXISTS idx_recipients_name ON recipients(name);
CREATE INDEX IF NOT EXISTS idx_recipients_department ON recipients(department);

CREATE INDEX IF NOT EXISTS idx_packages_tracking_no ON packages(tracking_no);
CREATE INDEX IF NOT EXISTS idx_packages_recipient_id ON packages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_packages_status ON packages(status);
CREATE INDEX IF NOT EXISTS idx_packages_created_at ON packages(created_at);
CREATE INDEX IF NOT EXISTS idx_packages_created_by ON packages(created_by);

CREATE INDEX IF NOT EXISTS idx_package_events_package_id ON package_events(package_id);
CREATE INDEX IF NOT EXISTS idx_package_events_actor_id ON package_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_package_events_created_at ON package_events(created_at);

CREATE INDEX IF NOT EXISTS idx_attachments_package_id ON attachments(package_id);
CREATE INDEX IF NOT EXISTS idx_attachments_uploaded_by ON attachments(uploaded_by);
"""


def init_database(db_path: str) -> None:
    """Initialize the database with the current schema."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = create_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()


def verify_schema(db_path: str) -> bool:
    """Return True when the required tables exist."""
    required_tables = {
        "users",
        "sessions",
        "auth_events",
        "recipients",
        "packages",
        "package_events",
        "attachments",
        "system_settings",
    }

    conn = create_connection(db_path)
    try:
        result = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        existing_tables = {row[0] for row in result}
        return required_tables.issubset(existing_tables)
    finally:
        conn.close()
