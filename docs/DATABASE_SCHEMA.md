# Database Schema Documentation

## Overview

The Mailroom Tracking System uses **DuckDB** as its embedded database. DuckDB is a high-performance analytical database that operates in-process, requiring no separate server installation. The database file is stored locally and uses Write-Ahead Logging (WAL) for transaction durability.

**Database File**: `./data/mailroom.duckdb`  
**Database Engine**: DuckDB 0.9+  
**Transaction Mode**: WAL (Write-Ahead Logging)  
**Character Encoding**: UTF-8

## Database Architecture

### Write Queue Pattern

To prevent database locking issues with concurrent writes, the system implements an async write queue pattern:

- All write operations are queued through a single async worker task
- Read operations use connection pooling for parallel execution
- Write operations are retried up to 3 times with exponential backoff on failure
- Database checkpoints occur every 1000 transactions or 5 minutes

### Connection Management

- **Write Operations**: Single connection through async queue
- **Read Operations**: Connection pool with multiple concurrent connections
- **Session Timeout**: 30 seconds for idle connections
- **Retry Logic**: 3 attempts with exponential backoff (100ms, 200ms, 400ms)

## Entity Relationship Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│    users    │────────<│   sessions   │         │ auth_events │
└─────────────┘         └──────────────┘         └─────────────┘
       │                                                  │
       │                                                  │
       │ created_by                                       │ user_id
       │                                                  │
       ▼                                                  ▼
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  packages   │────────<│package_events│         │             │
└─────────────┘         └──────────────┘         │             │
       │                       │                  │             │
       │ recipient_id          │ actor_id         │             │
       │                       │                  │             │
       ▼                       ▼                  ▼             │
┌─────────────┐         ┌──────────────┐                       │
│ recipients  │         │    users     │                       │
└─────────────┘         └──────────────┘                       │
       │                                                        │
       │                                                        │
       ▼                                                        │
┌─────────────┐                                                │
│ attachments │────────────────────────────────────────────────┘
└─────────────┘
```

## Tables

### users

Stores user accounts with authentication and authorization information.

**Purpose**: User authentication, authorization, and account management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique user identifier |
| username | VARCHAR | NOT NULL, UNIQUE | Login username (unique across system) |
| password_hash | VARCHAR | NOT NULL | Argon2id hashed password |
| full_name | VARCHAR | NOT NULL | User's full display name |
| role | VARCHAR | NOT NULL, CHECK IN ('super_admin', 'admin', 'operator') | User role for RBAC |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Account active status (soft delete) |
| must_change_password | BOOLEAN | NOT NULL, DEFAULT false | Force password change on next login |
| password_history | TEXT | NULL | JSON array of previous 3 password hashes |
| failed_login_count | INTEGER | NOT NULL, DEFAULT 0 | Counter for failed login attempts |
| locked_until | TIMESTAMP | NULL | Account lockout expiration timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last modification timestamp |

**Indexes**:
- `idx_users_username` on `username` - Fast login lookups
- `idx_users_role` on `role` - Role-based queries
- `idx_users_is_active` on `is_active` - Active user filtering

**Business Rules**:
- Username must be unique and cannot be changed after creation
- Password must meet complexity requirements (12+ chars, mixed case, symbols)
- Users cannot reuse their last 3 passwords
- Account locks after 5 failed login attempts for 30 minutes
- Super admin accounts cannot be modified by non-super admins

**Example Data**:
```sql
INSERT INTO users (username, password_hash, full_name, role) VALUES
('admin', '$argon2id$v=19$m=19456,t=3,p=1$...', 'System Administrator', 'super_admin'),
('john.operator', '$argon2id$v=19$m=19456,t=3,p=1$...', 'John Smith', 'operator');
```

---

### sessions

Stores active user sessions for authentication.

**Purpose**: Session-based authentication and activity tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique session identifier |
| user_id | UUID | NOT NULL, FOREIGN KEY → users(id) | Associated user account |
| token | VARCHAR | NOT NULL, UNIQUE | Secure session token (stored in cookie) |
| expires_at | TIMESTAMP | NOT NULL | Session expiration timestamp |
| last_activity | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last request timestamp |
| ip_address | VARCHAR | NULL | Client IP address |
| user_agent | TEXT | NULL | Client user agent string |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Session creation timestamp |

**Indexes**:
- `idx_sessions_token` on `token` - Fast session validation
- `idx_sessions_user_id` on `user_id` - User session queries
- `idx_sessions_expires_at` on `expires_at` - Expired session cleanup

**Business Rules**:
- Sessions expire after 30 minutes of inactivity
- Session expiration extends on each request
- Maximum 3 concurrent sessions per user
- Sessions are terminated when user is deactivated
- Expired sessions are cleaned up periodically

**Example Data**:
```sql
INSERT INTO sessions (user_id, token, expires_at, ip_address) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'abc123...', '2024-01-15 15:00:00', '192.168.1.100');
```

---

### auth_events

Audit log for authentication and authorization events.

**Purpose**: Security auditing and compliance tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique event identifier |
| user_id | UUID | NULL, FOREIGN KEY → users(id) | Associated user (NULL for failed logins) |
| event_type | VARCHAR | NOT NULL | Event type (login, logout, login_failed, etc.) |
| username | VARCHAR | NULL | Username attempted (for failed logins) |
| ip_address | VARCHAR | NULL | Client IP address |
| details | TEXT | NULL | JSON object with additional event data |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Event timestamp |

**Indexes**:
- `idx_auth_events_user_id` on `user_id` - User activity queries
- `idx_auth_events_event_type` on `event_type` - Event type filtering
- `idx_auth_events_created_at` on `created_at` - Time-based queries

**Event Types**:
- `login` - Successful login
- `logout` - User logout
- `login_failed` - Failed login attempt
- `password_changed` - Password change
- `password_reset` - Admin password reset
- `user_created` - New user account created
- `user_updated` - User account modified
- `user_deactivated` - User account deactivated
- `account_locked` - Account locked due to failed attempts
- `account_unlocked` - Account unlocked

**Business Rules**:
- All authentication events must be logged
- Logs are retained for minimum 365 days
- Failed login attempts include attempted username
- Successful logins include user_id and IP address

**Example Data**:
```sql
INSERT INTO auth_events (user_id, event_type, ip_address, details) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'login', '192.168.1.100', '{"user_agent": "Mozilla/5.0..."}');
```

---

### recipients

Stores employee information for package recipients.

**Purpose**: Package recipient directory and autocomplete

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique recipient identifier |
| employee_id | VARCHAR | NOT NULL, UNIQUE | Employee ID from HR system |
| name | VARCHAR | NOT NULL | Full name of recipient |
| email | VARCHAR | NOT NULL | Email address |
| department | VARCHAR | NULL | Department name |
| phone | VARCHAR | NULL | Phone number |
| location | VARCHAR | NULL | Office location or building |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Active status (soft delete) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last modification timestamp |

**Indexes**:
- `idx_recipients_employee_id` on `employee_id` - Employee ID lookups
- `idx_recipients_is_active` on `is_active` - Active recipient filtering
- `idx_recipients_name` on `name` - Name-based searches
- `idx_recipients_department` on `department` - Department filtering

**Business Rules**:
- Employee ID must be unique across all recipients
- Email must be valid format (contains @ and domain)
- Inactive recipients cannot receive new packages
- Recipients can be bulk imported via CSV
- Duplicate employee_id in CSV triggers update instead of insert

**Example Data**:
```sql
INSERT INTO recipients (employee_id, name, email, department, location) VALUES
('EMP001', 'Jane Doe', 'jane.doe@company.com', 'Engineering', 'Building A'),
('EMP002', 'Bob Smith', 'bob.smith@company.com', 'Marketing', 'Building B');
```

---

### packages

Stores package tracking information.

**Purpose**: Core package tracking and management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique package identifier |
| tracking_no | VARCHAR | NOT NULL | Carrier tracking number (non-unique) |
| carrier | VARCHAR | NOT NULL | Shipping carrier name |
| recipient_id | UUID | NOT NULL, FOREIGN KEY → recipients(id) | Package recipient |
| status | VARCHAR | NOT NULL, CHECK IN ('registered', 'awaiting_pickup', 'out_for_delivery', 'delivered', 'returned') | Current package status |
| notes | TEXT | NULL | Optional notes (max 500 chars) |
| created_by | UUID | NOT NULL, FOREIGN KEY → users(id) | Operator who registered package |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Registration timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last status change timestamp |

**Indexes**:
- `idx_packages_tracking_no` on `tracking_no` - Tracking number searches
- `idx_packages_recipient_id` on `recipient_id` - Recipient package queries
- `idx_packages_status` on `status` - Status filtering
- `idx_packages_created_at` on `created_at` - Date range queries
- `idx_packages_created_by` on `created_by` - Operator activity tracking

**Status Values**:
- `registered` - Package received and registered in system
- `awaiting_pickup` - Package ready for recipient pickup
- `out_for_delivery` - Package dispatched for delivery
- `delivered` - Package delivered to recipient
- `returned` - Package returned to sender

**Business Rules**:
- Tracking numbers are not unique (multiple packages can share same tracking number)
- Recipient must be active at time of registration
- Status changes create entries in package_events table
- Initial status is always 'registered'
- Only operators and admins can register packages

**Example Data**:
```sql
INSERT INTO packages (tracking_no, carrier, recipient_id, status, created_by) VALUES
('1Z999AA10123456784', 'UPS', '550e8400-e29b-41d4-a716-446655440001', 'registered', '550e8400-e29b-41d4-a716-446655440000');
```

---

### package_events

Audit trail for package status changes.

**Purpose**: Package status history and chain of custody

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique event identifier |
| package_id | UUID | NOT NULL, FOREIGN KEY → packages(id) | Associated package |
| old_status | VARCHAR | NULL | Previous status (NULL for initial registration) |
| new_status | VARCHAR | NOT NULL | New status after change |
| notes | TEXT | NULL | Optional notes about status change |
| actor_id | UUID | NOT NULL, FOREIGN KEY → users(id) | User who made the change |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Event timestamp |

**Indexes**:
- `idx_package_events_package_id` on `package_id` - Package timeline queries
- `idx_package_events_actor_id` on `actor_id` - User activity tracking
- `idx_package_events_created_at` on `created_at` - Time-based queries

**Business Rules**:
- Every status change creates a new event record
- Initial registration has old_status = NULL
- Events are immutable (never updated or deleted)
- Timeline is ordered by created_at ascending
- Actor must be authenticated user

**Example Data**:
```sql
INSERT INTO package_events (package_id, old_status, new_status, actor_id, notes) VALUES
('550e8400-e29b-41d4-a716-446655440010', NULL, 'registered', '550e8400-e29b-41d4-a716-446655440000', 'Package received at mailroom'),
('550e8400-e29b-41d4-a716-446655440010', 'registered', 'awaiting_pickup', '550e8400-e29b-41d4-a716-446655440000', 'Recipient notified');
```

---

### attachments

Stores metadata for package photos and attachments.

**Purpose**: Package photo management and file tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique attachment identifier |
| package_id | UUID | NOT NULL, FOREIGN KEY → packages(id) | Associated package |
| filename | VARCHAR | NOT NULL | Original filename |
| file_path | VARCHAR | NOT NULL | Relative path to stored file |
| mime_type | VARCHAR | NOT NULL | File MIME type |
| file_size | INTEGER | NOT NULL | File size in bytes |
| uploaded_by | UUID | NOT NULL, FOREIGN KEY → users(id) | User who uploaded file |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Upload timestamp |

**Indexes**:
- `idx_attachments_package_id` on `package_id` - Package attachment queries
- `idx_attachments_uploaded_by` on `uploaded_by` - User upload tracking

**Business Rules**:
- Maximum file size: 5MB
- Allowed MIME types: image/jpeg, image/png, image/webp
- Files stored in `/uploads/packages/YYYY/MM/` directory structure
- Filenames are generated with UUID to prevent conflicts
- Multiple photos can be attached to single package

**Example Data**:
```sql
INSERT INTO attachments (package_id, filename, file_path, mime_type, file_size, uploaded_by) VALUES
('550e8400-e29b-41d4-a716-446655440010', 'package-photo.jpg', 'packages/2024/01/abc123-photo.jpg', 'image/jpeg', 245678, '550e8400-e29b-41d4-a716-446655440000');
```

## Common Queries

### Get User with Role
```sql
SELECT id, username, full_name, role, is_active
FROM users
WHERE username = ? AND is_active = true;
```

### Validate Session
```sql
SELECT s.id, s.user_id, s.expires_at, u.username, u.role, u.is_active
FROM sessions s
JOIN users u ON s.user_id = u.id
WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP AND u.is_active = true;
```

### Search Recipients (Autocomplete)
```sql
SELECT id, employee_id, name, email, department
FROM recipients
WHERE is_active = true
  AND (name ILIKE ? OR email ILIKE ? OR employee_id ILIKE ?)
ORDER BY name
LIMIT 10;
```

### Get Package with Timeline
```sql
-- Package details
SELECT p.*, r.name as recipient_name, r.email as recipient_email, r.department,
       u.full_name as created_by_name
FROM packages p
JOIN recipients r ON p.recipient_id = r.id
JOIN users u ON p.created_by = u.id
WHERE p.id = ?;

-- Package timeline
SELECT pe.*, u.full_name as actor_name
FROM package_events pe
JOIN users u ON pe.actor_id = u.id
WHERE pe.package_id = ?
ORDER BY pe.created_at ASC;
```

### Dashboard Statistics
```sql
-- Packages registered today
SELECT COUNT(*) FROM packages WHERE DATE(created_at) = CURRENT_DATE;

-- Packages awaiting pickup
SELECT COUNT(*) FROM packages WHERE status = 'awaiting_pickup';

-- Packages delivered today
SELECT COUNT(*) FROM packages 
WHERE status = 'delivered' AND DATE(updated_at) = CURRENT_DATE;

-- Top recipients this month
SELECT r.name, r.department, COUNT(p.id) as package_count
FROM recipients r
JOIN packages p ON p.recipient_id = r.id
WHERE DATE_TRUNC('month', p.created_at) = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY r.id, r.name, r.department
ORDER BY package_count DESC
LIMIT 5;
```

### Search Packages with Filters
```sql
SELECT p.*, r.name as recipient_name, r.department
FROM packages p
JOIN recipients r ON p.recipient_id = r.id
WHERE 1=1
  AND (? IS NULL OR p.status = ?)
  AND (? IS NULL OR p.tracking_no ILIKE ?)
  AND (? IS NULL OR r.name ILIKE ?)
  AND (? IS NULL OR r.department = ?)
  AND (? IS NULL OR p.created_at >= ?)
  AND (? IS NULL OR p.created_at <= ?)
ORDER BY p.created_at DESC
LIMIT ? OFFSET ?;
```

## Database Maintenance

### Backup Procedures

**Daily Backup** (automated via PowerShell script):
```powershell
# Copy database file
Copy-Item "C:\MailroomApp\data\mailroom.duckdb" "C:\Backups\Mailroom\$(Get-Date -Format 'yyyyMMdd')"

# Compress backup
Compress-Archive -Path "C:\Backups\Mailroom\$(Get-Date -Format 'yyyyMMdd')" -DestinationPath "C:\Backups\Mailroom\$(Get-Date -Format 'yyyyMMdd').zip"
```

**Retention Policy**: 30 days of daily backups

### Cleanup Operations

**Expired Sessions** (runs every hour):
```sql
DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;
```

**Old Audit Logs** (runs monthly):
```sql
-- Archive logs older than 365 days
-- (Implementation depends on archival strategy)
```

### Performance Optimization

**Vacuum** (weekly):
```sql
VACUUM;
```

**Analyze** (monthly):
```sql
ANALYZE;
```

**Checkpoint** (automatic every 1000 transactions or 5 minutes):
```sql
CHECKPOINT;
```

## Migration Strategy

### Initial Migration

The initial migration creates all tables and indexes. It is executed automatically on first run via `scripts/init_database.ps1`.

### Future Migrations

Future schema changes should:
1. Create a new migration file in `app/database/migrations/`
2. Include both upgrade and downgrade logic
3. Be versioned sequentially
4. Be tested on a copy of production data

**Migration Template**:
```python
def upgrade(conn):
    """Apply migration."""
    conn.execute("""
        ALTER TABLE packages ADD COLUMN new_field VARCHAR;
    """)

def downgrade(conn):
    """Rollback migration."""
    conn.execute("""
        ALTER TABLE packages DROP COLUMN new_field;
    """)
```

## Troubleshooting

### Database Locked Error

**Symptom**: `database is locked` error during writes

**Solution**:
- Ensure all writes go through the async write queue
- Check for long-running transactions
- Verify WAL mode is enabled
- Restart the application to clear stale locks

### Slow Queries

**Symptom**: Queries taking longer than 200ms

**Solution**:
- Run `ANALYZE` to update statistics
- Check if indexes are being used (`EXPLAIN` query)
- Add indexes on frequently filtered columns
- Consider pagination for large result sets

### Database Corruption

**Symptom**: Integrity check failures

**Solution**:
- Stop the application immediately
- Restore from most recent backup
- Run integrity check: `PRAGMA integrity_check;`
- Contact support if corruption persists

## Security Considerations

### Access Control

- Database file permissions: Read/Write for application service account only
- No direct database access for users
- All access through application API with RBAC

### Data Protection

- Passwords stored as Argon2id hashes (never plaintext)
- Session tokens are cryptographically secure random values
- Sensitive data in audit logs is JSON-encoded
- Database backups should be encrypted at rest

### Compliance

- Audit logs retained for 365 days minimum
- All authentication events logged
- Package status changes tracked with actor and timestamp
- User modifications logged in auth_events

## Performance Benchmarks

**Expected Performance** (on typical Windows Server hardware):

| Operation | Target | Notes |
|-----------|--------|-------|
| User login | < 100ms | Including password verification |
| Session validation | < 10ms | Cached in memory |
| Package registration | < 50ms | Including event creation |
| Package search | < 200ms | Up to 10,000 packages |
| Recipient autocomplete | < 200ms | Up to 1,000 recipients |
| Dashboard statistics | < 200ms | Aggregated queries |
| CSV import (100 rows) | < 2s | Batch processing |

## Database Size Estimates

**Estimated Storage Requirements**:

| Data Type | Size per Record | 10,000 Records |
|-----------|----------------|----------------|
| User | ~500 bytes | ~5 MB |
| Session | ~300 bytes | ~3 MB |
| Auth Event | ~400 bytes | ~4 MB |
| Recipient | ~400 bytes | ~4 MB |
| Package | ~500 bytes | ~5 MB |
| Package Event | ~300 bytes | ~3 MB |
| Attachment | ~200 bytes | ~2 MB |

**Total Database Size** (1 year, 10,000 packages):
- Database file: ~50-100 MB
- Attachments (photos): ~2-5 GB (separate from database)

## References

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB SQL Reference](https://duckdb.org/docs/sql/introduction)
- [Write-Ahead Logging](https://duckdb.org/docs/connect/concurrency)
