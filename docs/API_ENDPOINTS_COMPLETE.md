# Complete API Endpoints Reference

## Overview

This document provides a complete reference for all API endpoints in the Mailroom Tracking System, organized by functional area.

**Base URL**: `https://mailroom.company.local`  
**API Version**: 1.0.0  
**Authentication**: Session-based (HttpOnly cookies)  
**Rate Limiting**: Varies by endpoint (see individual endpoints)

## Endpoint Summary

### Authentication
- `POST /auth/login` - Authenticate user
- `POST /auth/logout` - End session
- `GET /me` - Get current user
- `POST /me/password` - Change own password

### Packages
- `GET /packages` - List/search packages
- `POST /packages/new` - Register new package
- `GET /packages/:id` - Get package details
- `POST /packages/:id/status` - Update package status
- `POST /packages/:id/photo` - Add photo to package

### Recipients
- `GET /recipients/search` - Autocomplete search
- `GET /admin/recipients` - List recipients (Admin)
- `POST /admin/recipients/new` - Create recipient (Admin)
- `PUT /admin/recipients/:id/edit` - Update recipient (Admin)
- `POST /admin/recipients/:id/deactivate` - Deactivate recipient (Admin)
- `POST /admin/recipients/import` - CSV import (Admin)

### User Management
- `GET /admin/users` - List users (Admin)
- `POST /admin/users/new` - Create user (Admin)
- `PUT /admin/users/:id/edit` - Update user (Admin)
- `POST /admin/users/:id/deactivate` - Deactivate user (Admin)
- `POST /admin/users/:id/password` - Reset password (Admin)

### Dashboard & Reports
- `GET /dashboard` - Dashboard statistics
- `GET /admin/reports/export` - Export packages CSV (Admin)

### Audit Logs
- `GET /admin/audit-logs` - View audit logs (Super Admin)

### System
- `GET /health` - Health check (public)

## Detailed Endpoint Documentation

See `API_DOCUMENTATION.md` for detailed request/response examples for each endpoint.

## Role-Based Access Control

| Endpoint Pattern | Super Admin | Admin | Operator |
|-----------------|-------------|-------|----------|
| `/auth/*` | ✓ | ✓ | ✓ |
| `/me/*` | ✓ | ✓ | ✓ |
| `/dashboard` | ✓ | ✓ | ✓ |
| `/packages` (view/create/update) | ✓ | ✓ | ✓ |
| `/recipients/search` | ✓ | ✓ | ✓ |
| `/admin/recipients/*` | ✓ | ✓ | ✗ |
| `/admin/users/*` | ✓ | ✓* | ✗ |
| `/admin/reports/*` | ✓ | ✓ | ✗ |
| `/admin/audit-logs` | ✓ | ✗ | ✗ |

*Admin can only manage Operator accounts, not other Admins or Super Admin

## Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 423 | Locked | Account locked |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "field_errors": {
    "field_name": ["Error message"]
  }
}
```

### Paginated Response
```json
{
  "items": [ ... ],
  "total": 100,
  "skip": 0,
  "limit": 25,
  "has_more": true
}
```

## Rate Limiting

Rate limits are enforced per endpoint:

- **Login endpoint**: 10 requests/minute per IP
- **API endpoints**: 100 requests/minute per user
- **CSV import**: 10 requests/hour per user

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642258800
```

## CSRF Protection

All state-changing requests (POST, PUT, DELETE) require CSRF token:

1. Token is included in forms automatically
2. For API calls, retrieve from cookie: `csrf_token`
3. Include in header: `X-CSRF-Token: <token>`

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: `https://mailroom.company.local/docs`
- **ReDoc**: `https://mailroom.company.local/redoc`

These interfaces allow you to:
- Browse all endpoints
- View request/response schemas
- Test endpoints directly
- Download OpenAPI specification

## Testing Endpoints

### Using cURL

```bash
# Login
curl -X POST https://mailroom.company.local/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  -c cookies.txt

# Get packages (using saved cookies)
curl -X GET https://mailroom.company.local/packages \
  -b cookies.txt

# Register package with photo
curl -X POST https://mailroom.company.local/packages/new \
  -b cookies.txt \
  -F "tracking_no=1Z999AA10123456784" \
  -F "carrier=UPS" \
  -F "recipient_id=550e8400-e29b-41d4-a716-446655440010" \
  -F "photo=@package-photo.jpg"
```

### Using PowerShell

```powershell
# Login
$body = @{
    username = "admin"
    password = "password"
} | ConvertTo-Json

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$response = Invoke-RestMethod -Uri "https://mailroom.company.local/auth/login" `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -WebSession $session

# Get packages
$packages = Invoke-RestMethod -Uri "https://mailroom.company.local/packages" `
    -Method Get `
    -WebSession $session
```

### Using Python

```python
import requests

# Login
session = requests.Session()
response = session.post(
    "https://mailroom.company.local/auth/login",
    json={"username": "admin", "password": "password"}
)

# Get packages
packages = session.get("https://mailroom.company.local/packages").json()

# Register package
with open("photo.jpg", "rb") as f:
    response = session.post(
        "https://mailroom.company.local/packages/new",
        data={
            "tracking_no": "1Z999AA10123456784",
            "carrier": "UPS",
            "recipient_id": "550e8400-e29b-41d4-a716-446655440010"
        },
        files={"photo": f}
    )
```

## Webhooks (Future Feature)

Webhooks are not currently implemented but may be added in future versions to notify external systems of package events.

## API Versioning

Current version: v1 (implicit in all endpoints)

Future versions will be introduced as needed:
- Breaking changes: New version (v2)
- Non-breaking changes: Same version with deprecation notices

## Support

For API support:
- Documentation: This file and `API_DOCUMENTATION.md`
- Interactive docs: `/docs`
- Database schema: `DATABASE_SCHEMA.md`
- Configuration: `CONFIGURATION.md`
