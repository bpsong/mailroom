# Mailroom Tracking System - Test Suite

This directory contains the comprehensive test suite for the Mailroom Tracking System.

## Test Structure

```
tests/
├── unit/                    # Unit tests for services
│   ├── test_auth_service.py
│   ├── test_package_service.py
│   ├── test_recipient_service.py
│   └── test_user_service.py
├── integration/             # Integration tests for endpoints
│   ├── test_auth_endpoints.py
│   ├── test_rbac_endpoints.py
│   ├── test_package_lifecycle.py
│   └── test_csv_import.py
├── e2e/                     # End-to-end workflow tests
│   ├── test_operator_workflow.py
│   ├── test_admin_workflow.py
│   └── test_concurrent_operations.py
├── conftest.py              # Shared fixtures
├── test_rbac.py             # RBAC service tests
└── test_security_fixes.py   # Security implementation tests
```

## Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Unit Tests Only
```bash
python -m pytest tests/unit/ -v
```

### Run Integration Tests Only
```bash
python -m pytest tests/integration/ -v
```

### Run E2E Tests Only
```bash
python -m pytest tests/e2e/ -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

## Test Categories

### Unit Tests (27 tests)

Unit tests focus on testing individual service methods in isolation without database dependencies.

**AuthService Tests:**
- Password hashing and verification
- Password strength validation
- Password history checking and updates
- Session token generation

**PackageService Tests:**
- Package status validation
- Valid status transitions

**RecipientService Tests:**
- Email validation logic

**UserService Tests:**
- Role validation
- Role hierarchy

### Integration Tests (Skipped - Require Database Setup)

Integration tests verify endpoint behavior with full request/response cycles. These tests are currently skipped as they require:
- Database initialization
- CSRF token handling
- Session management
- Authentication flow

**Authentication Endpoints:**
- Login success/failure
- Account lockout
- Logout
- Session expiration

**RBAC Endpoints:**
- Operator access restrictions
- Admin access restrictions
- Super admin full access
- Admin cannot modify super admin

**Package Lifecycle:**
- Package registration
- Status updates
- Search and filtering
- Validation rules

**CSV Import:**
- Valid CSV import
- Duplicate handling (updates)
- Validation errors
- Missing columns
- Dry run mode

### End-to-End Tests (Skipped - Require Full Setup)

E2E tests verify complete user workflows from login to task completion.

**Operator Workflow:**
- Complete workflow: login → register → update status → delivered
- Search own packages
- Filter by status
- Photo upload

**Admin Workflow:**
- User management (create, edit, deactivate)
- Recipient management (manual and CSV import)
- Dashboard and reporting
- Cannot modify super admin

**Concurrent Operations:**
- Multiple operators registering packages simultaneously
- Concurrent status updates
- Multiple concurrent logins
- Session limit enforcement
- Database write queue under load

## Test Results

### Current Status

✅ **27 Unit Tests - All Passing**
- AuthService: 18 tests
- PackageService: 4 tests
- RecipientService: 3 tests
- UserService: 2 tests

⏭️ **Integration Tests - Skipped**
- Require database setup and authentication infrastructure
- Can be enabled by removing `@pytest.mark.skip` decorators
- Need to implement login helpers and fixtures

⏭️ **E2E Tests - Skipped**
- Require full application setup
- Need database initialization
- Need CSRF token handling
- Need session management

## Enabling Skipped Tests

To enable integration and E2E tests:

1. **Set up test database:**
   ```python
   # In conftest.py
   @pytest.fixture(scope="session")
   async def test_db():
       # Initialize test database
       # Run migrations
       yield
       # Cleanup
   ```

2. **Create authentication helpers:**
   ```python
   async def login_user(client, username, password):
       csrf_token = generate_csrf_token()
       client.cookies.set("csrf_token", csrf_token)
       response = client.post("/auth/login", data={...})
       return response
   ```

3. **Remove skip decorators:**
   ```python
   # Change from:
   @pytest.mark.skip(reason="Requires database setup")
   
   # To:
   # (no decorator)
   ```

## Test Coverage

The test suite covers:

✅ **Core Business Logic:**
- Password hashing and validation
- Session management
- RBAC permissions
- Package status workflow
- Email validation

✅ **Security Features:**
- CSRF protection
- Session limits
- Password history
- Account lockout

✅ **Data Validation:**
- Required fields
- Email format
- Password strength
- Status transitions

⏭️ **API Endpoints:** (Integration tests - skipped)
⏭️ **User Workflows:** (E2E tests - skipped)
⏭️ **Concurrent Operations:** (E2E tests - skipped)

## Notes

- Integration and E2E tests are marked as skipped to allow the test suite to run without full database setup
- These tests provide a comprehensive blueprint for testing once the infrastructure is in place
- Unit tests focus on core business logic and can run independently
- All unit tests are passing and provide good coverage of service layer logic
