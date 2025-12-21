# RBAC Implementation Summary

## Overview

This document summarizes the Role-Based Access Control (RBAC) implementation for the Mailroom Tracking System.

## Components Implemented

### 1. RBAC Service (`app/services/rbac_service.py`)

The `RBACService` provides centralized permission management with the following features:

#### Role Hierarchy
- **super_admin** (level 3): Full system access
- **admin** (level 2): Manage operators and recipients
- **operator** (level 1): Package handling only

#### Key Methods

- `can_manage_user(actor, target)`: Checks if actor can manage target user
  - Super admin can manage anyone
  - Admin can only manage operators
  - Operators cannot manage anyone

- `can_create_user_with_role(actor, target_role)`: Checks if actor can create user with specified role
  - Super admin can create any role
  - Admin can only create operators
  - Operators cannot create users

- `has_permission(user, permission)`: Checks if user has specific permission

- `get_user_permissions(user)`: Returns all permissions for a user's role

- `is_higher_role(role1, role2)`: Compares role hierarchy

- `can_modify_user_field(actor, target, field)`: Checks field-level modification permissions

### 2. Authentication Decorators (`app/decorators/auth.py`)

Three decorators for protecting routes:

#### `@require_auth`
Requires any authenticated user. Used for endpoints accessible by all logged-in users.

```python
@router.get("/packages")
@require_auth
async def list_packages(request: Request):
    # Accessible by operator, admin, super_admin
    pass
```

#### `@require_role(*allowed_roles)`
Requires specific role(s). Super admin automatically has access to all roles.

```python
@router.get("/admin/users")
@require_role("admin")
async def list_users(request: Request):
    # Accessible by admin, super_admin
    pass

@router.get("/admin/audit-logs")
@require_role("super_admin")
async def view_audit_logs(request: Request):
    # Accessible by super_admin only
    pass
```

#### `@require_permission(permission)`
Requires specific permission. Provides granular control beyond roles.

```python
@router.get("/admin/reports")
@require_permission("view_reports")
async def view_reports(request: Request):
    # Accessible by users with view_reports permission
    pass
```

### 3. Route Protection

All routes have been organized and protected according to the RBAC requirements:

#### Public Routes (No Authentication)
- `POST /auth/login` - User login
- `GET /health` - Health check
- `/static/*` - Static files

#### Authenticated Routes (All Users)
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user info
- `GET /dashboard` - Dashboard
- `GET /packages` - List packages
- `POST /packages/new` - Register package
- `GET /packages/{id}` - View package details
- `POST /packages/{id}/status` - Update package status
- `POST /packages/{id}/photo` - Add package photo
- `GET /recipients/search` - Search recipients
- `POST /me/password` - Change own password

#### Admin Routes (Admin + Super Admin)
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - List users
- `POST /admin/users/new` - Create user
- `PUT /admin/users/{id}/edit` - Edit user
- `POST /admin/users/{id}/deactivate` - Deactivate user
- `POST /admin/users/{id}/password` - Reset user password
- `GET /admin/recipients` - List recipients
- `POST /admin/recipients/new` - Create recipient
- `PUT /admin/recipients/{id}/edit` - Edit recipient
- `POST /admin/recipients/{id}/deactivate` - Deactivate recipient
- `POST /admin/recipients/import` - Import recipients from CSV
- `GET /admin/reports/export` - Export reports

#### Super Admin Only Routes
- `GET /admin/audit-logs` - View audit logs

## Permission Matrix

| Permission | Super Admin | Admin | Operator |
|-----------|-------------|-------|----------|
| view_dashboard | ✓ | ✓ | ✓ |
| register_package | ✓ | ✓ | ✓ |
| update_package_status | ✓ | ✓ | ✓ |
| view_packages | ✓ | ✓ | ✓ |
| search_recipients | ✓ | ✓ | ✓ |
| manage_recipients | ✓ | ✓ | ✗ |
| import_recipients | ✓ | ✓ | ✗ |
| view_reports | ✓ | ✓ | ✗ |
| export_reports | ✓ | ✓ | ✗ |
| manage_users | ✓ | ✓* | ✗ |
| manage_admins | ✓ | ✗ | ✗ |
| view_audit_logs | ✓ | ✗ | ✗ |
| manage_super_admin | ✓ | ✗ | ✗ |

*Admin can only manage operators, not other admins or super admins

## User Management Rules

### Creating Users
- **Super Admin**: Can create users with any role (super_admin, admin, operator)
- **Admin**: Can only create operators
- **Operator**: Cannot create users

### Editing Users
- **Super Admin**: Can edit any user including other super admins
- **Admin**: Can only edit operators
- **Operator**: Cannot edit other users (can only change own password)

### Deactivating Users
- **Super Admin**: Can deactivate any user
- **Admin**: Can only deactivate operators
- **Operator**: Cannot deactivate users

### Password Reset
- **Super Admin**: Can reset password for any user
- **Admin**: Can only reset passwords for operators
- **All Users**: Can change their own password via `/me/password`

## Testing

Comprehensive tests have been implemented in `tests/test_rbac.py` covering:

- User management permissions (can_manage_user)
- User creation permissions (can_create_user_with_role)
- Permission checking (has_permission, get_user_permissions)
- Role hierarchy (is_higher_role)
- Field-level modification permissions (can_modify_user_field)

All tests pass successfully.

## Usage Examples

### Protecting a Route

```python
from fastapi import APIRouter, Request
from app.decorators import require_role, get_current_user

router = APIRouter()

@router.post("/admin/users/new")
@require_role("admin")
async def create_user(request: Request):
    user = get_current_user(request)
    # Implementation here
    pass
```

### Checking Permissions in Code

```python
from app.services.rbac_service import rbac_service
from app.decorators import get_current_user

@router.put("/admin/users/{user_id}")
@require_role("admin")
async def edit_user(request: Request, user_id: str):
    actor = get_current_user(request)
    
    # Get target user from database
    target = get_user_by_id(user_id)
    
    # Check if actor can manage target
    if not rbac_service.can_manage_user(actor, target):
        raise HTTPException(
            status_code=403,
            detail="You cannot manage this user"
        )
    
    # Proceed with edit
    pass
```

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **Requirement 2.5**: Super admin cannot be modified by other users
- **Requirement 3.1**: Operators cannot access admin endpoints (403 Forbidden)
- **Requirement 3.2**: Admins cannot access super admin endpoints (403 Forbidden)
- **Requirement 3.3**: Super admin can manage all users
- **Requirement 3.4**: Admin can only manage operators
- **Requirement 3.5**: All users can change their own password

## Next Steps

The RBAC infrastructure is now in place. Future tasks will implement the actual business logic for:

- User management (Task 5)
- Recipient management (Task 6)
- Package tracking (Task 7)
- Dashboard and reporting (Task 8)
- Audit logging (Task 9)

All these implementations will use the RBAC decorators and service methods established in this task.
