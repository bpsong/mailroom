# Security Fixes Documentation

This document summarizes security fixes that were applied and their current behavior in code.

## 1. CSRF Enforcement Fix

### Prior issue
CSRF checks were too permissive for unsafe requests.

### Current behavior
- Middleware validates `X-CSRF-Token` when provided.
- Form-based unsafe requests must be validated in route handlers with:
  - `csrf_token: str = Form(...)`
  - `validate_csrf_token(request, csrf_token)`

### Relevant code
- `app/middleware/csrf.py`
- Routes in `app/routes/auth.py`, `app/routes/admin.py`, `app/routes/packages.py`, `app/routes/user.py`

### Correct test pattern
Use real route paths and include CSRF tokens.

Example targets:
- `POST /admin/users/new`
- `POST /packages/new`
- `POST /admin/recipients/import/validate`

## 2. Concurrent Session Limit Enforcement

### Prior issue
Session creation did not enforce max concurrent sessions.

### Current behavior
- `create_session()` enforces `MAX_CONCURRENT_SESSIONS`.
- Oldest active sessions are removed when limit is exceeded.

### Relevant code
- `app/services/auth_service.py`
- `app/config.py` (`max_concurrent_sessions`)

## 3. Recipient Department Requirement

### Prior issue
Recipient department could be missing in flows that should require it.

### Current behavior
- CSV validation requires department.
- Startup migration manager backfills empty/NULL departments to `Unassigned`.
- Service/model-level validation enforces non-empty department on create/update flows.

### Relevant code
- `app/services/csv_import_service.py`
- `app/database/migrations.py` (`_enforce_recipient_department_requirement`)
- recipient models/services

## Configuration Reminders

Ensure `.env` includes security values:

```env
MAX_CONCURRENT_SESSIONS=3
MAX_FAILED_LOGINS=5
ACCOUNT_LOCKOUT_DURATION=1800
PASSWORD_MIN_LENGTH=12
PASSWORD_HISTORY_COUNT=3
```

## Operational Checklist

1. Validate CSRF behavior on state-changing forms.
2. Validate session rollover when exceeding concurrent session cap.
3. Validate recipient imports reject rows with missing department.
4. Monitor auth/audit logs after deployment.
