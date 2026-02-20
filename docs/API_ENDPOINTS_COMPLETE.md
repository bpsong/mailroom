# Complete API Endpoints Reference

## Overview

This application is primarily an HTML + HTMX web app (not a pure JSON REST API).

- Base URL: `https://mailroom.company.local`
- Auth: Session cookie (`session_token`)
- CSRF: Required for state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`)
- Public routes: `/auth/login`, `/auth/logout`, `/me/force-password-change`, `/health`, `/docs`, `/redoc`, `/openapi.json`

## Endpoint Summary

### Core System
- `GET /` - Redirect to login page
- `GET /health` - Health check JSON

### Authentication
- `GET /auth/login` - Login page
- `POST /auth/login` - Authenticate user (form post, sets `session_token` cookie)
- `POST /auth/logout` - Logout (form post, clears session cookie)
- `GET /auth/me` - Current authenticated user info (JSON)

### User Self-Service (`/me`)
- `GET /me/profile` - Profile page
- `GET /me/sessions` - Active sessions page
- `POST /me/sessions/{session_id}/terminate` - Terminate own session
- `GET /me/force-password-change` - Forced password change page
- `POST /me/force-password-change` - Submit forced password change
- `GET /me/password` - Change password page
- `POST /me/password` - Submit own password change

### Dashboard
- `GET /dashboard` - Dashboard page

### Packages (`/packages`)
- `GET /packages` - List/search packages
- `GET /packages/new` - Registration form
- `POST /packages/new` - Register new package
- `GET /packages/{package_id}` - Package detail page
- `POST /packages/{package_id}/status` - Update package status
- `POST /packages/{package_id}/photo` - Attach photo
- `GET /packages/{package_id}/qrcode/download` - Download QR PNG
- `GET /packages/{package_id}/qrcode/print` - Print-friendly QR page

### Recipients (`/recipients`)
- `GET /recipients` - Recipient list page
- `GET /recipients/search` - Recipient autocomplete (HTML partial or JSON)

### Admin (`/admin`)
- `GET /admin/dashboard` - Admin dashboard JSON

#### Admin Users
- `GET /admin/users` - User list page
- `GET /admin/users/new` - Create user page
- `GET /admin/users/{user_id}/edit` - Edit user page
- `POST /admin/users/new` - Create user
- `PUT /admin/users/{user_id}/edit` - Update user
- `POST /admin/users/{user_id}/deactivate` - Deactivate user
- `POST /admin/users/{user_id}/password` - Reset user password

#### Admin Recipients
- `GET /admin/recipients` - Recipient list page
- `GET /admin/recipients/new` - Create recipient page
- `POST /admin/recipients/new` - Create recipient
- `GET /admin/recipients/{recipient_id}/edit` - Edit recipient page
- `POST /admin/recipients/{recipient_id}/edit` - Update recipient
- `PUT /admin/recipients/{recipient_id}/edit` - Update recipient
- `POST /admin/recipients/{recipient_id}/deactivate` - Deactivate recipient
- `GET /admin/recipients/import` - CSV import page
- `POST /admin/recipients/import/validate` - Validate CSV upload
- `POST /admin/recipients/import/confirm` - Execute CSV import

#### Admin Reports
- `GET /admin/reports` - Reports page
- `GET /admin/reports/preview` - Report preview (HTML)
- `GET /admin/reports/export` - Export packages CSV

#### Super Admin
- `GET /admin/settings` - System settings page
- `POST /admin/settings/qr-base-url` - Update QR base URL
- `GET /admin/audit-logs` - Audit logs page

## Access Matrix

| Area | Super Admin | Admin | Operator |
|---|---|---|---|
| `/auth/*` | Yes | Yes | Yes |
| `/me/*` | Yes | Yes | Yes |
| `/dashboard` | Yes | Yes | Yes |
| `/packages/*` | Yes | Yes | Yes |
| `/recipients/*` | Yes | Yes | Yes |
| `/admin/users/*` | Yes | Limited | No |
| `/admin/recipients/*` | Yes | Yes | No |
| `/admin/reports/*` | Yes | Yes | No |
| `/admin/settings*` | Yes | No | No |
| `/admin/audit-logs` | Yes | No | No |

`Limited`: Admin can manage operators only.

## Request/Response Notes

- Login (`POST /auth/login`) expects `application/x-www-form-urlencoded` with:
  - `username`, `password`, `csrf_token`, optional `next`
- Login response is JSON and sets the `session_token` cookie.
- Most routes render HTML templates; some admin/actions return redirects or JSON.
- CSRF token can be sent as form field (`csrf_token`) and/or `X-CSRF-Token` header.

## Deprecated/Not Implemented

- No WebSocket endpoint is implemented.
- No `/users` root API (without `/admin`) is implemented.
- No `DELETE /packages/{id}` endpoint is implemented.

## Related Docs

- `docs/API_DOCUMENTATION.md`
- `docs/CONFIGURATION.md`
- `docs/SECURITY_IMPLEMENTATION.md`
- `docs/DATABASE_SCHEMA.md`
