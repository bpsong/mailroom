# API Documentation

## Overview

Mailroom Tracking is an HTMX + server-rendered FastAPI app. Most endpoints render HTML (full pages or partial fragments), while a smaller set returns JSON or files.

- Base URL: `https://mailroom.company.local`
- API version: `1.0.0`
- Auth model: session cookie (`session_token`)
- CSRF: enforced for state-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`)
- OpenAPI source of truth: `/docs`, `/redoc`, `/openapi.json` when API docs are enabled

Public endpoints:
- `/auth/login`
- `/auth/logout`
- `/me/force-password-change`
- `/health`

Documentation endpoints:
- `/docs`, `/redoc`, and `/openapi.json` are available outside production.
- In production, they are disabled unless `ENABLE_API_DOCS=true`.

## Authentication Flow

1. Client loads `GET /auth/login`.
2. Client submits credentials to `POST /auth/login` with CSRF token.
3. Server validates lockout state, account state, and password.
4. On success, server returns JSON with `redirect_url` and sets `session_token` cookie.
5. Auth middleware validates session on protected routes.

### Login example

Request (`application/x-www-form-urlencoded`):
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=jdoe&password=secret&csrf_token=...&next=/packages
```

Success response (`200 OK`, JSON):
```json
{
  "success": true,
  "message": "Login successful",
  "redirect_url": "/packages",
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
- `401`: invalid username/password
- `403`: CSRF failure, account inactive, or account locked

## Content Types

- Form submissions: `application/x-www-form-urlencoded`
- File uploads: `multipart/form-data`
- HTML pages/partials: `text/html`
- JSON responses: `application/json`
- QR download: `image/png`

## Core Endpoints

### `GET /`
Redirects to `/auth/login`.

### `GET /health`
Returns health JSON (database, disk, uptime, and related checks).

## Authentication Endpoints (`/auth`)

### `GET /auth/login`
Renders login page.

### `POST /auth/login`
Authenticates user.

Form fields:
- `username` (required)
- `password` (required)
- `csrf_token` (required)
- `next` (optional)

Behavior notes:
- Returns JSON (not redirect) with `redirect_url` for client navigation.
- If `next` is `/login` or `/auth/login`, fallback is `/dashboard`.
- If user must rotate password, `redirect_url` becomes `/me/force-password-change`.

### `POST /auth/logout`
Terminates session (if present), deletes `session_token`, and redirects to `/auth/login` with `303 See Other`.

Form fields:
- `csrf_token` (required)

### `GET /auth/me`
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

- `GET /me/profile` — Profile page
- `GET /me/sessions` — Active sessions page
- `POST /me/sessions/{session_id}/terminate` — Terminate own session (form + CSRF)
- `GET /me/force-password-change` — Forced password change page
- `POST /me/force-password-change` — Forced password change submit
- `GET /me/password` — Change password page
- `POST /me/password` — Change own password submit (form + CSRF)

Forced password change notes:
- `GET /me/force-password-change` and `POST /me/force-password-change` intentionally do not use `@require_auth`; they validate session cookie directly so first-login/admin-reset users can complete rotation.

## Dashboard

### `GET /dashboard`
Renders dashboard with summary stats/distributions.

## Package Endpoints (`/packages`)

### `GET /packages`
List/search page.

Query params:
- `query` (optional)
- `status` (optional)
- `department` (optional)
- `date_from` (optional ISO date/time)
- `date_to` (optional ISO date/time)
- `page` (default `1`)
- `limit` (default `25`, max `100`)

### `GET /packages/new`
Renders package registration form.

### `POST /packages/new`
Registers package and optional photo.

Form fields:
- `tracking_no` (required)
- `carrier` (required)
- `recipient_id` (required UUID)
- `notes` (optional)
- `photo` (optional upload)
- `csrf_token` (required)

Success behavior:
- Returns HTML success template (`packages/register_success.html`) for HTMX/browser flow.

### `GET /packages/{package_id}`
Renders package detail page with timeline, attachments, and QR preview.

### `POST /packages/{package_id}/status`
Updates package status and returns HTML partial/template (`packages/status_updated.html`).

Form fields:
- `status` (required)
- `notes` (optional)
- `csrf_token` (required)

### `POST /packages/{package_id}/photo`
Adds photo attachment and returns HTML fragment/template (`packages/photo_added.html`).

Form fields:
- `photo` (required)
- `csrf_token` (required)

### `GET /packages/{package_id}/qrcode/download`
Returns QR PNG as attachment (`image/png`).

### `GET /packages/{package_id}/qrcode/print`
Renders print-friendly QR page.

## Recipient Endpoints (`/recipients`)

### `GET /recipients`
Renders recipient list page.

Query params:
- `q` (optional; query text)
- `dept` (optional department filter)
- `page` (default `1`)
- `limit` (default `25`, min `10`, max `100`)

### `GET /recipients/search`
Recipient autocomplete.

Query params:
- `q` (optional)
- `limit` (default `10`, max `50`)

Response behavior:
- Returns HTML partial when `Accept: text/html` or HTMX headers are present.
- Returns JSON recipient list otherwise.

## Admin Endpoints (`/admin`)

### `GET /admin/dashboard`
Returns lightweight admin dashboard JSON.

### User management
- `GET /admin/users`
- `GET /admin/users/new`
- `GET /admin/users/{user_id}/edit`
- `POST /admin/users/new`
- `PUT /admin/users/{user_id}/edit`
- `POST /admin/users/{user_id}/deactivate`
- `POST /admin/users/{user_id}/password`

### Recipient management
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

### Super-admin only
- `GET /admin/settings`
- `POST /admin/settings/qr-base-url`
- `GET /admin/audit-logs`

## Rate Limiting

Current middleware limits:
- `/auth/login`: `RATE_LIMIT_LOGIN` per minute (default 10)
- All other non-exempt routes: `RATE_LIMIT_API` per minute (default 100)

Exempt routes:
- `/health`, `/static/*`, `/uploads/*`
- `/docs`, `/redoc`, `/openapi.json` when API docs are enabled

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
