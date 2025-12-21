# Security Implementation

This document describes the security features implemented in the Mailroom Tracking System.

## Overview

The application implements multiple layers of security to protect against common web vulnerabilities and ensure data integrity.

## 1. CSRF Protection

**Implementation**: `app/middleware/csrf.py`

### Features
- CSRF token generation using cryptographically secure random values
- Token validation on all state-changing requests (POST, PUT, PATCH, DELETE)
- Separate tokens for cookie and form/header validation
- Automatic token injection into responses

### Usage
- CSRF tokens are automatically generated and set as cookies
- Forms must include the CSRF token as a hidden field or in the `X-CSRF-Token` header
- Login endpoint validates CSRF tokens before processing credentials

### Configuration
- Exempt routes: `/auth/login`, `/health`, static files
- Token storage: Session cookie with `secure=True` and `samesite=strict`

## 2. Rate Limiting

**Implementation**: `app/middleware/rate_limit.py`

### Features
- In-memory sliding window rate limiter
- Per-IP and per-endpoint rate limiting
- Configurable limits for different endpoints
- Automatic cleanup of old entries

### Limits
- Login endpoint: 10 requests per minute per IP
- General API: 100 requests per minute per IP
- Exempt routes: `/health`, `/docs`, static files

### Response
- Returns HTTP 429 (Too Many Requests) when limit exceeded
- Includes `Retry-After` header with 60-second wait time

### Configuration
Settings in `.env`:
```env
RATE_LIMIT_LOGIN=10
RATE_LIMIT_API=100
```

## 3. Input Sanitization

**Implementation**: `app/utils/sanitization.py`

### Features

#### SQL Injection Prevention
- All database queries use parameterized queries with placeholders
- No direct string concatenation of user input into SQL
- Dynamic WHERE clauses built from hardcoded strings with parameters

#### XSS Prevention
- Jinja2 auto-escaping enabled by default for all HTML templates
- Additional sanitization utilities for special cases
- Content-Security-Policy headers restrict script execution

#### File Upload Validation
- File type validation by content (magic bytes), not just extension
- File size limits (5MB for images)
- Filename sanitization to prevent directory traversal
- Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`

### Utilities
- `sanitize_filename()`: Remove path components and dangerous characters
- `sanitize_search_query()`: Limit length and remove null bytes
- `sanitize_html_input()`: Remove control characters
- `validate_uuid()`: Ensure UUID format
- `validate_file_type()`: Check file extension against allowed types
- `validate_file_content()`: Validate file by magic bytes

## 4. Security Headers

**Implementation**: `app/middleware/security_headers.py`

### Headers Applied

#### Strict-Transport-Security (HSTS)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```
- Forces HTTPS for 1 year
- Applies to all subdomains
- Only enabled in production

#### X-Content-Type-Options
```
X-Content-Type-Options: nosniff
```
- Prevents MIME type sniffing
- Browsers must respect declared content types

#### X-Frame-Options
```
X-Frame-Options: DENY
```
- Prevents clickjacking attacks
- Disallows iframe embedding

#### X-XSS-Protection
```
X-XSS-Protection: 1; mode=block
```
- Enables browser XSS protection
- Blocks page rendering if XSS detected

#### Referrer-Policy
```
Referrer-Policy: strict-origin-when-cross-origin
```
- Controls referrer information
- Full URL for same-origin, origin only for cross-origin

#### Content-Security-Policy
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; ...
```
- Restricts resource loading
- Allows HTMX from CDN
- Allows inline styles for daisyUI
- Prevents XSS and data injection attacks

#### Permissions-Policy
```
Permissions-Policy: geolocation=(), microphone=(), camera=(self), ...
```
- Disables unnecessary browser features
- Allows camera for package photos
- Blocks geolocation, microphone, payment, USB

## 5. Cookie Security

### Session Cookie
```python
response.set_cookie(
    key="session_token",
    value=session.token,
    httponly=True,      # Prevents JavaScript access
    secure=True,        # HTTPS only
    samesite="lax",     # CSRF protection
    max_age=None,       # Session cookie
)
```

### CSRF Token Cookie
```python
response.set_cookie(
    key="csrf_token",
    value=csrf_token,
    httponly=False,     # JavaScript needs to read this
    secure=True,        # HTTPS only
    samesite="strict",  # Strict CSRF protection
    max_age=None,       # Session cookie
)
```

## 6. Authentication Security

### Password Security
- Argon2id hashing algorithm
- Time cost: 3
- Memory cost: 19456 KiB (19MB)
- Parallelism: 1

### Password Requirements
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Cannot reuse last 3 passwords

### Account Lockout
- 5 failed login attempts within 15 minutes
- 30-minute lockout period
- All attempts logged to audit trail

### Session Management
- 30-minute idle timeout
- Automatic session renewal on activity
- Maximum 3 concurrent sessions per user
- Secure session token generation

## Middleware Order

Middleware is executed in reverse order of addition:

1. **SecurityHeadersMiddleware** (executed first)
   - Adds security headers to all responses

2. **RateLimitMiddleware**
   - Enforces rate limits before processing requests

3. **CSRFMiddleware**
   - Validates CSRF tokens on state-changing requests

4. **AuthenticationMiddleware** (executed last)
   - Validates session and injects user into request

## Testing Security Features

### CSRF Protection
```bash
# Should fail without CSRF token
curl -X POST http://localhost:8000/packages/new \
  -H "Cookie: session_token=..." \
  -d "tracking_no=TEST123"

# Should succeed with CSRF token
curl -X POST http://localhost:8000/packages/new \
  -H "Cookie: session_token=...; csrf_token=..." \
  -H "X-CSRF-Token: ..." \
  -d "tracking_no=TEST123"
```

### Rate Limiting
```bash
# Make 11 rapid login attempts
for i in {1..11}; do
  curl -X POST http://localhost:8000/auth/login \
    -d "username=test&password=test"
done
# 11th request should return 429
```

### Security Headers
```bash
# Check security headers
curl -I http://localhost:8000/dashboard
# Should include X-Content-Type-Options, X-Frame-Options, CSP, etc.
```

## Best Practices

### For Developers

1. **Always use parameterized queries**
   ```python
   # Good
   conn.execute("SELECT * FROM users WHERE id = ?", [user_id])
   
   # Bad
   conn.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
   ```

2. **Sanitize file uploads**
   ```python
   from app.utils import validate_file_content
   
   mime_type = validate_file_content(content, allowed_types)
   if not mime_type:
       raise ValueError("Invalid file type")
   ```

3. **Use CSRF tokens in forms**
   ```html
   <form method="POST" action="/packages/new">
       <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
       <!-- form fields -->
   </form>
   ```

4. **Trust Jinja2 auto-escaping**
   ```html
   <!-- Safe - auto-escaped -->
   <p>{{ user.username }}</p>
   
   <!-- Dangerous - only use for trusted content -->
   <p>{{ content | safe }}</p>
   ```

### For Administrators

1. **Use HTTPS in production**
   - Configure Caddy or nginx as reverse proxy
   - Obtain valid TLS certificates
   - Set `APP_ENV=production` in `.env`

2. **Monitor rate limits**
   - Check logs for rate limit violations
   - Adjust limits if legitimate users are affected

3. **Review audit logs**
   - Monitor failed login attempts
   - Investigate suspicious activity
   - Check for unusual patterns

4. **Keep dependencies updated**
   - Regularly update Python packages
   - Monitor security advisories
   - Test updates in staging environment

## Security Checklist

- [x] CSRF protection on all state-changing requests
- [x] Rate limiting on login and API endpoints
- [x] SQL injection prevention with parameterized queries
- [x] XSS prevention with Jinja2 auto-escaping
- [x] File upload validation by content
- [x] HttpOnly and Secure flags on session cookies
- [x] Content-Security-Policy header
- [x] HSTS header (production only)
- [x] X-Frame-Options header
- [x] X-Content-Type-Options header
- [x] Strong password requirements
- [x] Account lockout after failed attempts
- [x] Session timeout and renewal
- [x] Audit logging for security events

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Content Security Policy Reference](https://content-security-policy.com/)
