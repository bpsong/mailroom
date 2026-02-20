# Security Implementation

This document reflects the current security controls implemented in code.

## Security Layers

- Authentication middleware: `app/middleware/auth.py`
- CSRF middleware: `app/middleware/csrf.py`
- Rate limiting middleware: `app/middleware/rate_limit.py`
- Security headers middleware: `app/middleware/security_headers.py`
- Auth/session logic: `app/services/auth_service.py`

## 1. Authentication & Session Security

- Session cookie name: `session_token`
- Cookie flags:
  - `HttpOnly=True`
  - `SameSite=Lax`
  - `Secure` only when `APP_ENV=production`
- Session renewal is performed on authenticated activity.
- Session timeout is controlled by `SESSION_TIMEOUT`.
- Maximum concurrent sessions per user is enforced via `MAX_CONCURRENT_SESSIONS`.

## 2. Password Security

- Password hashing uses Argon2 (`argon2-cffi`) with configurable parameters:
  - `ARGON2_TIME_COST`
  - `ARGON2_MEMORY_COST`
  - `ARGON2_PARALLELISM`
- Password strength validation enforces:
  - minimum length (`PASSWORD_MIN_LENGTH`)
  - uppercase, lowercase, digit, special character
- Password history checks prevent reuse of recent passwords (`PASSWORD_HISTORY_COUNT`).

## 3. Account Lockout

- Failed login count is tracked per user.
- Lockout threshold is `MAX_FAILED_LOGINS`.
- Lockout duration is `ACCOUNT_LOCKOUT_DURATION` seconds.
- On success, failed counter resets.

Important behavior note:
- Current logic is threshold-based using stored failed counts and `locked_until`.
- There is no separate "N attempts within X-minute rolling window" policy implemented in middleware/service.

## 4. CSRF Protection

### Middleware behavior

- Protected methods: `POST`, `PUT`, `PATCH`, `DELETE`
- Exempt exact routes: `/health`
- Exempt prefixes: `/static/`, `/uploads/`, `/docs`, `/redoc`, `/openapi.json`

### Validation model

- Cookie token (`csrf_token`) is required.
- Header-based validation (`X-CSRF-Token`) is fully validated in middleware.
- For form posts, middleware requires route-level validation via `validate_csrf_token(request, form_token)`.
- Routes handling form posts are expected to include and validate a form field named `csrf_token`.

## 5. Rate Limiting

- Login route limit: `RATE_LIMIT_LOGIN` per minute (`/auth/login`)
- Default non-exempt route limit: `RATE_LIMIT_API` per minute
- Exempt routes:
  - `/health`, `/docs`, `/redoc`, `/openapi.json`
  - `/static/*`, `/uploads/*`

On exceed, middleware returns `429` JSON with `Retry-After: 60`.

## 6. Security Headers

Applied to responses by `SecurityHeadersMiddleware`:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (self + explicit allowed sources)
- `Permissions-Policy` (restricts sensitive browser features)
- `Strict-Transport-Security` only in production

## 7. Input and File Safety

- SQL queries use parameterized query patterns.
- Utility sanitizers are provided in `app/utils/sanitization.py`.
- File handling validates allowed MIME/content types and size constraints.

## 8. Audit & Security Event Logging

Security-relevant events are recorded in `auth_events` and logged through `audit_service`.

Examples:
- `login`, `login_failed`, `logout`
- `password_changed`, `password_reset`
- `user_management`
- `recipient_import`
- `system_settings_change`

## 9. Middleware Execution Order

Middleware is added in this order in `app/main.py`:
1. `AuthenticationMiddleware`
2. `CSRFMiddleware`
3. `RateLimitMiddleware`
4. `SecurityHeadersMiddleware`

Starlette executes middleware in reverse-add order for request handling.

## 10. Operational Recommendations

- Run with `APP_ENV=production` behind HTTPS reverse proxy.
- Keep `SECRET_KEY` strong and unique per deployment.
- Monitor failed login and rate-limit patterns in logs.
- Review audit logs regularly for privileged/admin actions.
