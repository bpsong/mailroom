"""Database schema definitions and initialization."""

import duckdb
from pathlib import Path

# SQL schema for all tables
SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL CHECK (role IN ('super_admin', 'admin', 'operator')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    must_change_password BOOLEAN NOT NULL DEFAULT false,
    password_history TEXT,  -- JSON array of previous password hashes
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token VARCHAR NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Authentication events table
CREATE TABLE IF NOT EXISTS auth_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    event_type VARCHAR NOT NULL,
    username VARCHAR,
    ip_address VARCHAR,
    details TEXT,  -- JSON for additional event data
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Recipients table
CREATE TABLE IF NOT EXISTS recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE,
    department VARCHAR,
    phone VARCHAR,
    location VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Packages table
CREATE TABLE IF NOT EXISTS packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tracking_no VARCHAR NOT NULL,
    carrier VARCHAR NOT NULL,
    recipient_id UUID NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('registered', 'awaiting_pickup', 'out_for_delivery', 'delivered', 'returned')),
    notes TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipient_id) REFERENCES recipients(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Package events table (audit trail for status changes)
-- Note: No foreign keys due to DuckDB limitations with UPDATE operations
CREATE TABLE IF NOT EXISTS package_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL,
    old_status VARCHAR,
    new_status VARCHAR NOT NULL,
    notes TEXT,
    actor_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Attachments table (for package photos)
-- Note: No foreign keys due to DuckDB limitations with UPDATE operations
CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    mime_type VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_by UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
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
    """
    Initialize the database with schema.
    
    Args:
        db_path: Path to the DuckDB database file
    """
    # Ensure the directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect and create schema
    conn = duckdb.connect(db_path)
    try:
        # Execute schema creation
        conn.execute(SCHEMA_SQL)
        
        # Commit changes
        conn.commit()
    finally:
        conn.close()


def verify_schema(db_path: str) -> bool:
    """
    Verify that all required tables exist in the database.
    
    Args:
        db_path: Path to the DuckDB database file
        
    Returns:
        True if all tables exist, False otherwise
    """
    required_tables = {
        'users', 'sessions', 'auth_events', 'recipients',
        'packages', 'package_events', 'attachments'
    }
    
    conn = duckdb.connect(db_path, read_only=True)
    try:
        result = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        
        existing_tables = {row[0] for row in result}
        return required_tables.issubset(existing_tables)
    finally:
        conn.close()
