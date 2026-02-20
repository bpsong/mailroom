# API Documentation

## Overview

Mailroom Tracking is an HTMX + server-rendered FastAPI app. Most endpoints render HTML (full pages or partials), while a smaller set returns JSON or files.

- Base URL: `https://mailroom.company.local`
- API version: `1.0.0`
- Auth model: Session cookie (`session_token`)
- CSRF: enforced for state-changing methods
- Public endpoints: `/auth/login`, `/auth/logout`, `/me/force-password-change`, `/health`, `/docs`, `/redoc`, `/openapi.json`

## Authentication Flow

1. Client loads `/auth/login` and receives CSRF token cookie.
2. Client posts credentials + CSRF token to `/auth/login`.
3. Server validates credentials and lockout rules.
4. Server returns JSON and sets `session_token` cookie.
5. Middleware validates and renews session on protected requests.

## Content Types

- Form submissions: `application/x-www-form-urlencoded`
- File uploads: `multipart/form-data`
- HTML pages/partials: `text/html`
- JSON responses: `application/json`
- QR download: `image/png`

## Core Endpoints

### GET /
Redirects to `/auth/login`.

### GET /health
Returns system health JSON from database/disk/uptime checks.

### GET /auth/login
Renders login page.

### POST /auth/login
Authenticates user.

Form fields:
- `username` (required)
- `password` (required)
- `csrf_token` (required)
- `next` (optional)

Success response (`200 OK`, JSON):
```json
{
  "success": true,
  "message": "Login successful",
  "redirect_url": "/dashboard",
  "user": {
    "id": "uuid",
    "username": "jdoe",
    "full_name": "Jane Doe",
    "role": "operator",
    "must_change_password": false
  }
}
```

Cookie set:
- `session_token` (`HttpOnly`, `SameSite=Lax`, `Secure` only in production)

Common errors:
- `401`: invalid credentials
- `403`: account inactive/locked or CSRF failure

### POST /auth/logout
Terminates session and clears `session_token` cookie.

Form fields:
- `csrf_token` (required)

Success: redirects to `/auth/login`.

### GET /auth/me
Returns current authenticated user JSON:
```json
{
  "id": "uuid",
  "username": "jdoe",
  "full_name": "Jane Doe",
  "role": "operator",
  "must_change_password": false
}
```

## User Self-Service Endpoints (`/me`)

- `GET /me/profile` - Profile page
- `GET /me/sessions` - Active sessions page
- `POST /me/sessions/{session_id}/terminate` - Terminate own session (form + CSRF)
- `GET /me/force-password-change` - Forced password change page
- `POST /me/force-password-change` - Forced password change submit
- `GET /me/password` - Change password page
- `POST /me/password` - Change own password (form + CSRF)

## Dashboard

### GET /dashboard
Renders dashboard page with summary stats and distributions.

## Package Endpoints (`/packages`)

### GET /packages
List/search page.

Query params:
- `query` (optional)
- `status` (optional)
- `department` (optional)
- `date_from` (optional ISO date/time)
- `date_to` (optional ISO date/time)
- `page` (default `1`)
- `limit` (default `25`, max `100`)

### GET /packages/new
Renders package registration form.

### POST /packages/new
Registers package and optional photo.

Form fields:
- `tracking_no` (required)
- `carrier` (required)
- `recipient_id` (required UUID)
- `notes` (optional)
- `photo` (optional upload)
- `csrf_token` (required)

Success: returns registration success HTML template.

### GET /packages/{package_id}
Renders package detail page with timeline, attachments, and QR code.

### POST /packages/{package_id}/status
Updates package status.

Form fields:
- `status` (required)
- `notes` (optional)
- `csrf_token` (required)

### POST /packages/{package_id}/photo
Adds photo attachment.

Form fields:
- `photo` (required)
- `csrf_token` (required)

### GET /packages/{package_id}/qrcode/download
Returns QR PNG as attachment.

### GET /packages/{package_id}/qrcode/print
Renders print-friendly QR page.

## Recipient Endpoints (`/recipients`)

### GET /recipients
Renders recipient list page.

Query params:
- `q` (optional; alias for query text)
- `dept` (optional)
- `page` (default `1`)
- `limit` (default `25`, min `10`, max `100`)

### GET /recipients/search
Recipient autocomplete.

Query params:
- `q` (optional)
- `limit` (default `10`, max `50`)

Response behavior:
- Returns HTML partial for HTMX/browser accepts HTML.
- Returns JSON recipient array for non-HTML API-style calls.

## Admin Endpoints (`/admin`)

### GET /admin/dashboard
Returns lightweight admin dashboard JSON.

### User Management
- `GET /admin/users`
- `GET /admin/users/new`
- `GET /admin/users/{user_id}/edit`
- `POST /admin/users/new`
- `PUT /admin/users/{user_id}/edit`
- `POST /admin/users/{user_id}/deactivate`
- `POST /admin/users/{user_id}/password`

### Recipient Management
- `GET /admin/recipients`
- `GET /admin/recipients/new`
- `POST /admin/recipients/new`
- `GET /admin/recipients/{recipient_id}/edit`
- `POST /admin/recipients/{recipient_id}/edit`
- `PUT /admin/recipients/{recipient_id}/edit`
- `POST /admin/recipients/{recipient_id}/deactivate`
- `GET /admin/recipients/import`
- `POST /admin/recipients/import/validate`
- `POST /admin/recipients/import/confirm`

### Reporting
- `GET /admin/reports`
- `GET /admin/reports/preview`
- `GET /admin/reports/export` (CSV download)

### Super Admin Only
- `GET /admin/settings`
- `POST /admin/settings/qr-base-url`
- `GET /admin/audit-logs`

## Rate Limiting

Current middleware limits:
- `/auth/login`: `RATE_LIMIT_LOGIN` per minute (default 10)
- all other non-exempt routes: `RATE_LIMIT_API` per minute (default 100)

Exempt from rate limiting:
- `/health`, `/docs`, `/redoc`, `/openapi.json`, `/static/*`, `/uploads/*`

## Error Shape

Most JSON errors use:
```json
{
  "detail": "Error message"
}
```

Some middleware responses use:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message"
  }
}
```

## Not Implemented

- No WebSocket endpoint (`/ws`) is implemented.
- No root `/users` API namespace is implemented.
- No package deletion endpoint is implemented.
