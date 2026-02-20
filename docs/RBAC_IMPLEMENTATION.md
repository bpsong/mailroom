# RBAC Implementation Summary

## Overview

Role-based access control is implemented via:

- `app/services/rbac_service.py`
- `app/decorators/auth.py`
- route decorators in `app/routes/*.py`

## Roles

- `super_admin`
- `admin`
- `operator`

Hierarchy: `super_admin > admin > operator`

## Core Rules

### User management
- Super Admin can manage all users.
- Admin can manage operators only.
- Operators cannot manage users.

### Role assignment
- Super Admin can create any role.
- Admin can create operators only.

### Field-level edit
- Role changes require Super Admin.

## Route Protection Patterns

- `@require_auth` for authenticated routes
- `@require_role("admin")` for admin/super_admin routes
- `@require_role("super_admin")` for super-admin-only routes

## Current Route Access Map

### Public (middleware-allowed)
- `/auth/login`
- `/auth/logout`
- `/me/force-password-change`
- `/health`
- docs/static routes

### All authenticated users
- `/dashboard`
- `/packages/*`
- `/recipients/*`
- `/me/profile`, `/me/sessions`, `/me/password`
- `/auth/me`

### Admin + Super Admin
- `/admin/users/*`
- `/admin/recipients/*`
- `/admin/reports*`
- `/admin/dashboard`

### Super Admin only
- `/admin/settings`
- `/admin/settings/qr-base-url`
- `/admin/audit-logs`

## Important Notes

- Admin permissions on `/admin/users/*` are still constrained by service-level RBAC checks (cannot manage admin/super_admin users).
- Deactivation and password reset operations include additional safety checks (for example, self-deactivation prevention).

## Test Coverage

RBAC service behaviors are covered in `tests/test_rbac.py`.
