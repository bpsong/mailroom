# Security Fixes Summary

This file is a retained summary of the major security hardening work already merged into the app.

## Implemented fixes

### 1. CSRF protection

- State-changing requests require CSRF validation.
- HTMX requests send the `X-CSRF-Token` header.
- Form submissions include a `csrf_token` field.

### 2. Concurrent session limits

- Users are limited to a configurable maximum number of concurrent sessions.
- Oldest sessions are evicted when the limit is exceeded.

### 3. Recipient department requirement

- Recipients require a non-empty department value.
- Existing data can be normalized with `scripts/backfill_recipient_departments.py` when needed.

## Operational notes

- Use [docs/SECURITY_FIXES.md](docs/SECURITY_FIXES.md) and [docs/SECURITY_IMPLEMENTATION.md](docs/SECURITY_IMPLEMENTATION.md) for current implementation detail.
- Use [scripts/backup.ps1](scripts/backup.ps1) before production maintenance.
- Follow the deployment docs for restart and recovery procedures instead of older one-off rollback instructions.

## Status

- Historical summary retained for context.
- Current security behavior should be verified against the test suite and the main documentation set.
