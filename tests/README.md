# Mailroom Tracking System - Test Suite

This directory contains the SQLite-backed test suite for the Mailroom Tracking System.

## Test Structure

```text
tests/
|-- unit/            # Unit tests for services and database helpers
|-- integration/     # Endpoint-level tests
|-- e2e/             # Full workflow tests
|-- conftest.py      # Shared fixtures and SQLite test database setup
|-- test_rbac.py
`-- test_security_fixes.py
```

## Running Tests on This Workspace

This repo has a known Windows `PATH` issue where Git Unix tooling can interfere with pytest startup. Use PowerShell, reset `PATH`, and invoke pytest through the explicit interpreter.

### Run the full suite

```powershell
$env:PATH='C:\Python313;C:\Python313\Scripts;C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem'
$env:SECRET_KEY='test-secret-key'
$env:APP_ENV='testing'
C:\Python313\python.exe -m pytest -v
```

### Run subsets

```powershell
C:\Python313\python.exe -m pytest tests\unit -v
C:\Python313\python.exe -m pytest tests\integration -v
C:\Python313\python.exe -m pytest tests\e2e -v
C:\Python313\python.exe -m pytest tests --cov=app --cov-report=html
```

## Current Status

- The active suite covers unit, integration, E2E, RBAC, security, and concurrent-write behavior.
- The SQLite migration is covered by the current tests.
- A recent full run completed with `95 passed`.

## Coverage Areas

- Authentication, password policy, and session handling
- RBAC enforcement
- Recipient CRUD and CSV import flows
- Package registration and status changes
- Dashboard, reporting, and audit behavior
- SQLite connection lifecycle and serialized writes
- Concurrent login, import, and write-load scenarios

## Notes

- `tests/conftest.py` provisions an isolated SQLite test database per run.
- Some warnings may still appear from upstream deprecations in Pydantic, Starlette, or `datetime.utcnow()` usage. They do not currently block the suite.
- For workspace-specific test guidance, see the root [AGENTS.md](../AGENTS.md).
