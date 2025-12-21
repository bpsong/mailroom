# Security Fixes Documentation

This document describes the critical security fixes implemented to address vulnerabilities in the Mailroom Tracking System.

## Issues Fixed

### 1. CSRF Protection Implementation

**Issue:** CSRF protection was effectively disabled. The middleware returned `True` for every unsafe request whenever a `csrf_token` cookie existed without comparing it to any value sent by the client.

**Impact:** All state-changing endpoints (user management, password change, package updates, CSV import, etc.) could be triggered via cross-site POSTs, violating requirement 15.3.

**Fix:**
- Updated `app/middleware/csrf.py` to properly validate CSRF tokens
- Modified `_validate_csrf_token()` to return `False` by default for form submissions
- Routes must now explicitly call `validate_csrf_token()` to verify form tokens
- HTMX requests must include `X-CSRF-Token` header
- Added CSRF token meta tag to `templates/base.html`
- Created `app/utils/csrf_helpers.py` with helper functions

**Implementation Details:**

1. **Middleware Changes:**
   - Header-based validation (for AJAX/HTMX): Compares `X-CSRF-Token` header with cookie
   - Form-based validation: Stores expected token in `request.state` for route-level validation
   - Returns `False` for form submissions requiring explicit validation

2. **Template Changes:**
   - Added `<meta name="csrf-token" content="{{ csrf_token }}">` to base template
   - HTMX automatically reads this and includes it in requests via the configured event handler

3. **Route Requirements:**
   - All POST/PUT/PATCH/DELETE routes must either:
     - Accept `X-CSRF-Token` header (for HTMX/AJAX)
     - Call `validate_csrf_token(request, form_token)` for form submissions
     - Include `csrf_token` as a form field

**Testing:**
```python
# Test CSRF protection
import requests

# This should fail without CSRF token
response = requests.post(
    "http://localhost:8000/admin/users",
    data={"username": "test", "password": "test123"},
)
assert response.status_code == 403

# This should succeed with valid CSRF token
session = requests.Session()
# Get CSRF token from cookie
response = session.get("http://localhost:8000/admin/users/new")
csrf_token = session.cookies.get("csrf_token")

# Include token in form
response = session.post(
    "http://localhost:8000/admin/users",
    data={
        "username": "test",
        "password": "test123",
        "csrf_token": csrf_token
    },
)
assert response.status_code == 200
```

### 2. Session Limit Enforcement

**Issue:** Session creation never enforced the "max 3 concurrent sessions per user" rule from requirement 12.5. `create_session` blindly inserted a row each time, allowing unlimited simultaneous browser sessions.

**Impact:** A single credential set could keep unlimited simultaneous browser sessions alive, defeating the intended containment for compromised accounts.

**Fix:**
- Updated `app/services/auth_service.py` `create_session()` method
- Added session count check before creating new sessions
- Automatically terminates oldest sessions when limit is exceeded
- Added `max_concurrent_sessions` configuration to `app/config.py`

**Implementation Details:**

1. **Session Limit Logic:**
   ```python
   # Check current active session count
   active_sessions = get_active_sessions_for_user(user_id)
   
   # If at or over limit, delete oldest sessions
   if len(active_sessions) >= max_concurrent_sessions:
       sessions_to_delete = len(active_sessions) - max_concurrent_sessions + 1
       delete_oldest_sessions(sessions_to_delete)
   
   # Create new session
   create_new_session()
   ```

2. **Configuration:**
   - Added `max_concurrent_sessions: int = 3` to `Settings` class
   - Can be overridden via environment variable: `MAX_CONCURRENT_SESSIONS=5`

3. **Behavior:**
   - When a user logs in and already has 3 active sessions
   - The oldest session is automatically terminated
   - New session is created
   - User is notified via audit log

**Testing:**
```python
# Test session limit
async def test_session_limit():
    user_id = UUID("...")
    
    # Create 3 sessions
    session1 = await auth_service.create_session(user_id)
    session2 = await auth_service.create_session(user_id)
    session3 = await auth_service.create_session(user_id)
    
    # Verify all 3 are active
    assert await auth_service.validate_session(session1.token) is not None
    assert await auth_service.validate_session(session2.token) is not None
    assert await auth_service.validate_session(session3.token) is not None
    
    # Create 4th session
    session4 = await auth_service.create_session(user_id)
    
    # Verify oldest (session1) is terminated
    assert await auth_service.validate_session(session1.token) is None
    assert await auth_service.validate_session(session2.token) is not None
    assert await auth_service.validate_session(session3.token) is not None
    assert await auth_service.validate_session(session4.token) is not None
```

### 3. Department Field Requirement

**Issue:** Recipient creation did not require a department even though requirement 5.1 makes it mandatory. The Pydantic model marked `department` as optional and the service wrote whatever value (including `None`) it received.

**Impact:** Recipients could be created without a department, preventing the department-based filtering/reporting called for in requirements 5 and 9.

**Fix:**
- Updated `app/models/recipient.py` to make `department` required
- Added validation in `app/services/recipient_service.py` to ensure department is not empty
- Updated all recipient models (`Recipient`, `RecipientCreate`, `RecipientPublic`, `RecipientSearchResult`)

**Implementation Details:**

1. **Model Changes:**
   ```python
   # Before
   department: Optional[str] = Field(None, max_length=100)
   
   # After
   department: str = Field(..., min_length=1, max_length=100)
   ```

2. **Service Validation:**
   ```python
   # Validate department is provided and not empty
   if not recipient_data.department or not recipient_data.department.strip():
       raise ValueError("Department is required and cannot be empty")
   ```

3. **Database Migration:**
   - Existing recipients with `NULL` department need to be backfilled
   - See migration script below

**Data Migration:**

Create and run the following script to backfill missing department data:

```python
# scripts/backfill_recipient_departments.py
"""Backfill missing department data for existing recipients."""

import asyncio
from app.database.connection import get_db
from app.database.write_queue import get_write_queue


async def backfill_departments():
    """Backfill NULL departments with 'Unknown'."""
    db = get_db()
    
    # Check for recipients with NULL department
    with db.get_read_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM recipients WHERE department IS NULL"
        ).fetchone()
        
        null_count = result[0]
        print(f"Found {null_count} recipients with NULL department")
    
    if null_count == 0:
        print("No recipients need backfilling")
        return
    
    # Update NULL departments to 'Unknown'
    write_queue = await get_write_queue()
    await write_queue.execute(
        """
        UPDATE recipients
        SET department = 'Unknown', updated_at = CURRENT_TIMESTAMP
        WHERE department IS NULL
        """
    )
    
    print(f"Updated {null_count} recipients with department='Unknown'")
    print("Please review and update these recipients with correct departments")


if __name__ == "__main__":
    asyncio.run(backfill_departments())
```

**Testing:**
```python
# Test department requirement
async def test_department_required():
    from app.models import RecipientCreate
    from pydantic import ValidationError
    
    # This should fail
    try:
        recipient = RecipientCreate(
            employee_id="EMP001",
            name="John Doe",
            email="john@example.com",
            # department missing
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass  # Expected
    
    # This should succeed
    recipient = RecipientCreate(
        employee_id="EMP001",
        name="John Doe",
        email="john@example.com",
        department="Engineering",
    )
    assert recipient.department == "Engineering"
```

## Configuration Updates

### Environment Variables

Add the following to your `.env` file:

```bash
# Session Management
MAX_CONCURRENT_SESSIONS=3  # Maximum concurrent sessions per user
```

### .env.example

Update `.env.example` with the new configuration:

```bash
# Security
SESSION_TIMEOUT=1800
MAX_CONCURRENT_SESSIONS=3
MAX_FAILED_LOGINS=5
ACCOUNT_LOCKOUT_DURATION=1800
PASSWORD_MIN_LENGTH=12
PASSWORD_HISTORY_COUNT=3
```

## Deployment Checklist

When deploying these fixes:

1. **Backup Database:**
   ```powershell
   .\scripts\backup.ps1
   ```

2. **Update Code:**
   ```bash
   git pull origin main
   ```

3. **Run Department Backfill:**
   ```bash
   python scripts/backfill_recipient_departments.py
   ```

4. **Update Configuration:**
   - Add `MAX_CONCURRENT_SESSIONS=3` to `.env`

5. **Restart Application:**
   ```powershell
   Restart-Service MailroomTracking
   ```

6. **Verify CSRF Protection:**
   - Test form submissions work correctly
   - Test HTMX requests include CSRF token
   - Verify unauthorized requests are blocked

7. **Monitor Logs:**
   - Check for CSRF validation failures
   - Monitor session creation/termination
   - Review recipient creation errors

## Security Recommendations

1. **CSRF Token Rotation:**
   - Consider rotating CSRF tokens on each request
   - Implement token expiration (currently session-based)

2. **Session Management:**
   - Monitor for unusual session patterns
   - Consider adding session fingerprinting (IP + User-Agent)
   - Implement session activity logging

3. **Department Validation:**
   - Consider maintaining a whitelist of valid departments
   - Implement department autocomplete to prevent typos
   - Add department management interface for admins

4. **Regular Security Audits:**
   - Review authentication logs weekly
   - Monitor failed CSRF validations
   - Check for suspicious session patterns

## References

- Requirement 15.3: CSRF Protection
- Requirement 12.5: Session Management
- Requirement 5.1: Recipient Department Requirement
- OWASP CSRF Prevention Cheat Sheet
- OWASP Session Management Cheat Sheet
