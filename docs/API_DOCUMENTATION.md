# API Documentation

## Overview

The Mailroom Tracking System is an HTMX-based web application built with FastAPI. The system uses HTML forms and HTMX for dynamic interactions rather than a traditional JSON REST API. All endpoints require authentication via session cookies except for the login and health check endpoints.

**Architecture**: HTMX + HTML Forms (not JSON REST API)

**Base URL**: `https://mailroom.company.local`

**API Version**: 1.0.0

**Authentication**: Session-based with HttpOnly, Secure cookies

**Content Types**: 
- Request: `application/x-www-form-urlencoded` (HTML forms) or `multipart/form-data` (file uploads)
- Response: `text/html` (full pages or HTMX partial responses)

**Interactive Documentation**: `https://mailroom.company.local/docs` (FastAPI Swagger UI - for reference only)

**Note**: This documentation describes the actual HTMX/form-based implementation. The system does not expose a JSON REST API. All interactions use HTML forms with CSRF protection and return HTML responses (full pages or HTMX partials).

## Authentication Flow

1. Client sends credentials to `/auth/login`
2. Server validates credentials and creates session
3. Server returns session cookie (HttpOnly, Secure, SameSite=Lax)
4. Client includes cookie in subsequent requests
5. Server validates session on each request
6. Session expires after 30 minutes of inactivity
7. Client can explicitly logout via `/auth/logout`

## Authentication Endpoints

### POST /auth/login

Authenticate a user and create a session.

**Access**: Public (no authentication required)

**Rate Limit**: 10 requests per minute per IP

**Request**: `application/x-www-form-urlencoded` (HTML form)

**Form Fields**:
- `username` (required): User's username
- `password` (required): User's password
- `csrf_token` (required): CSRF protection token

**Success Response** (303 See Other):
- Redirects to `/dashboard` on successful login
- Sets session cookie: `session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/`

**Error Responses**:

**401 Unauthorized** - Invalid credentials:
```json
{
  "detail": "Invalid username or password"
}
```

**403 Forbidden** - Account locked:
```json
{
  "detail": "Account locked due to too many failed login attempts. Try again in 30 minutes."
}
```

**403 Forbidden** - CSRF validation failed:
```json
{
  "detail": "CSRF token validation failed"
}
```

**Business Rules**:
- Account locks after 5 consecutive failed attempts for 30 minutes
- Failed attempts are logged in auth_events table
- Session expires after 30 minutes of inactivity
- Maximum 3 concurrent sessions per user
- Session cookie does not include Max-Age (session-scoped)

---

### POST /auth/logout

End the current user session and clear session cookie.

**Access**: Authenticated users only

**Request**: `application/x-www-form-urlencoded` (HTML form)

**Form Fields**:
- `csrf_token` (required): CSRF protection token

**Success Response** (303 See Other):
- Redirects to `/auth/login`
- Clears session cookie

**Business Rules**:
- Session is deleted from database
- Session cookie is cleared
- Logout event is logged in auth_events table

---

### GET /me

Get current authenticated user information.

**Access**: Authenticated users only

**Request Body**: None

**Success Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.smith",
  "full_name": "John Smith",
  "role": "operator",
  "is_active": true,
  "must_change_password": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses**:

**401 Unauthorized** - Not authenticated:
```json
{
  "detail": "Not authenticated"
}
```

---

### POST /me/password

Change current user's password (self-service).

**Access**: Authenticated users only

**Request Body**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!",
  "confirm_password": "NewSecurePassword456!"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

**Error Responses**:

**400 Bad Request** - Current password incorrect:
```json
{
  "detail": "Current password is incorrect"
}
```

**422 Unprocessable Entity** - Password validation failed:
```json
{
  "detail": "Password must be at least 12 characters and contain uppercase, lowercase, digit, and special character"
}
```

**422 Unprocessable Entity** - Password reuse:
```json
{
  "detail": "Cannot reuse any of your last 3 passwords"
}
```

**Business Rules**:
- Password must meet complexity requirements (12+ chars, mixed case, symbols)
- Cannot reuse last 3 passwords
- Password change is logged in auth_events table
- must_change_password flag is cleared after successful change

---

## Package Management Endpoints

### GET /packages

List and search packages with filtering and pagination.

**Access**: All authenticated users

**Rate Limit**: 100 requests per minute per user

**Response**: HTML page (HTMX-compatible partial when `HX-Request` header present)

**Query Parameters**:
- `query` (optional): Search query for tracking number or recipient name (partial match)
- `status` (optional): Filter by status (`registered`, `awaiting_pickup`, `out_for_delivery`, `delivered`, `returned`)
- `department` (optional): Filter by recipient department (partial match)
- `date_from` (optional): Filter by created_at >= date_from (ISO 8601 format)
- `date_to` (optional): Filter by created_at <= date_to (ISO 8601 format)
- `page` (optional): Page number (1-indexed, default: 1)
- `limit` (optional): Items per page (default: 25, max: 100)

**Example Request**:
```
GET /packages?status=awaiting_pickup&department=Engineering&page=1&limit=25
```

**Success Response** (200 OK):
Returns HTML page with package list table. When requested via HTMX (with `HX-Request` header), returns partial HTML template for seamless updates.

**Performance**: Response time < 200ms for up to 10,000 packages

---

### GET /packages/{package_id}

Get detailed information about a specific package including timeline.

**Access**: All authenticated users

**Path Parameters**:
- `package_id` (required): UUID of the package

**Success Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "tracking_no": "1Z999AA10123456784",
  "carrier": "UPS",
  "recipient": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "employee_id": "EMP001",
    "name": "Jane Doe",
    "email": "jane.doe@company.com",
    "department": "Engineering",
    "phone": "+1-555-0123",
    "location": "Building A"
  },
  "status": "awaiting_pickup",
  "notes": "Handle with care",
  "created_by": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john.operator",
    "full_name": "John Smith"
  },
  "created_at": "2024-01-15T14:30:00Z",
  "updated_at": "2024-01-15T15:00:00Z",
  "photos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "filename": "package-photo.jpg",
      "url": "/uploads/packages/2024/01/abc123-photo.jpg",
      "uploaded_at": "2024-01-15T14:30:00Z"
    }
  ],
  "timeline": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "old_status": null,
      "new_status": "registered",
      "notes": "Package received at mailroom",
      "actor": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "full_name": "John Smith"
      },
      "created_at": "2024-01-15T14:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440031",
      "old_status": "registered",
      "new_status": "awaiting_pickup",
      "notes": "Recipient notified via email",
      "actor": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "full_name": "John Smith"
      },
      "created_at": "2024-01-15T15:00:00Z"
    }
  ]
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Package not found"
}
```

---

### GET /packages/{package_id}/qrcode/download

Download a PNG representation of the package QR code sized for 2 cm × 2 cm sticker printing.

**Access**: All authenticated users

**Response**: `image/png` binary payload with `Content-Disposition: attachment; filename=qr_code_{package_id}.png`

**Path Parameters**:
- `package_id` (required): UUID of the package

**Behavior**:
- Uses the configured QR base URL (Admin setting) or falls back to the incoming request host.
- Returns 404 if the package does not exist.
- PNG metadata includes 300 DPI to maintain print fidelity.

**Error Responses**:
- `404 Not Found` – Package missing or user lacks permission.
- `500 Internal Server Error` – Unexpected QR generation failure (see application logs).

---

### GET /packages/{package_id}/qrcode/print

Serve a print-optimized HTML view that contains only the QR code and tracking number.

**Access**: All authenticated users

**Response**: HTML page with inline CSS sized for 2 cm × 2 cm stickers; intended to be opened in a new tab and printed via the browser’s dialog.

**Path Parameters**:
- `package_id` (required): UUID of the package

**Behavior**:
- Embeds the QR image as a base64 data URI.
- Includes a client-side `Print QR Code` button (`window.print()`).
- Hides navigation and non-essential UI in `@media print` styles.

**Error Responses**:
- `404 Not Found` – Package not found.
- `500 Internal Server Error` – Unexpected QR generation failure.

---

### POST /packages/new

Register a new package (Operator/Admin only).

**Access**: Operator, Admin, Super Admin

**Request**: `multipart/form-data` (HTML form with optional file upload)

**Response**: HTML partial (HTMX-compatible)

**Form Fields**:
- `tracking_no` (required): Carrier tracking number
- `carrier` (required): Shipping carrier name
- `recipient_id` (required): UUID of recipient
- `notes` (optional): Additional notes (max 500 chars)
- `photo` (optional): Package photo file (max 5MB, JPEG/PNG/WebP)
- `csrf_token` (required): CSRF protection token

**Success Response** (200 OK):
Returns HTML partial showing success message and package details. HTMX swaps this into the page.

**Error Responses**:

**400 Bad Request** - Invalid recipient:
```json
{
  "detail": "Recipient not found or inactive"
}
```

**403 Forbidden** - CSRF validation failed:
```json
{
  "detail": "CSRF token validation failed"
}
```

**413 Payload Too Large** - Photo too large:
```json
{
  "detail": "File size exceeds maximum of 5MB"
}
```

**422 Unprocessable Entity** - Invalid file type:
```json
{
  "detail": "Invalid file type. Allowed types: JPEG, PNG, WebP"
}
```

**Business Rules**:
- Initial status is always "registered"
- Recipient must be active
- Photo is optional but recommended
- Package event is automatically created
- Operator who created package is recorded

---

### POST /packages/{package_id}/status

Update package status with optional notes.

**Access**: Operator, Admin, Super Admin

**Path Parameters**:
- `package_id` (required): UUID of the package

**Request**: `application/x-www-form-urlencoded` (HTML form)

**Response**: HTML partial (HTMX-compatible)

**Form Fields**:
- `status` (required): New status value
- `notes` (optional): Additional notes about the status change
- `csrf_token` (required): CSRF protection token

**Valid Status Values**:
- `registered` - Package received at mailroom
- `awaiting_pickup` - Ready for recipient pickup
- `out_for_delivery` - Package dispatched for delivery
- `delivered` - Successfully delivered to recipient
- `returned` - Returned to sender

**Success Response** (200 OK):
Returns HTML partial with updated package information. HTMX swaps this into the page.

**Error Responses**:

**400 Bad Request** - Invalid status transition:
```json
{
  "detail": "Cannot transition from 'delivered' to 'awaiting_pickup'"
}
```

**403 Forbidden** - CSRF validation failed:
```json
{
  "detail": "CSRF token validation failed"
}
```

**Business Rules**:
- Status change creates entry in package_events table
- Actor (current user) is recorded
- Cannot change status of delivered/returned packages

---

### POST /packages/{package_id}/photo

Add a photo to an existing package.

**Access**: Operator, Admin, Super Admin

**Path Parameters**:
- `package_id` (required): UUID of the package

**Request**: `multipart/form-data`
- `photo` (required): Image file (max 5MB, JPEG/PNG/WebP)

**Success Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "package_id": "550e8400-e29b-41d4-a716-446655440001",
  "filename": "package-photo.jpg",
  "url": "/uploads/packages/2024/01/abc123-photo.jpg",
  "file_size": 245678,
  "mime_type": "image/jpeg",
  "uploaded_by": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "John Smith"
  },
  "created_at": "2024-01-15T14:35:00Z"
}
```

**Error Responses**:

**404 Not Found** - Package not found:
```json
{
  "detail": "Package not found"
}
```

**413 Payload Too Large**:
```json
{
  "detail": "File size exceeds maximum of 5MB"
}
```

**422 Unprocessable Entity** - Invalid file type:
```json
{
  "detail": "Invalid file type. Allowed types: JPEG, PNG, WebP"
}
```

**Business Rules**:
- Multiple photos can be attached to a single package
- Photos are stored with unique filenames to prevent conflicts
- Original filename is preserved in metadata

---

### DELETE /packages/{package_id}

Delete a package (Admin only).

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Package deleted successfully"
}
```

---

---

## Recipient Management Endpoints

### GET /recipients/search

Autocomplete search for recipients (all authenticated users).

**Access**: All authenticated users

**Query Parameters**:
- `q` (required): Search query (min 2 characters)
- `active_only` (optional): Filter active recipients only (default: true)
- `limit` (optional): Maximum results to return (default: 10, max: 50)

**Example Request**:
```
GET /recipients/search?q=jane&active_only=true&limit=10
```

**Success Response** (200 OK):
```json
{
  "recipients": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "employee_id": "EMP001",
      "name": "Jane Doe",
      "email": "jane.doe@company.com",
      "department": "Engineering",
      "location": "Building A"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "employee_id": "EMP042",
      "name": "Jane Smith",
      "email": "jane.smith@company.com",
      "department": "Marketing",
      "location": "Building B"
    }
  ],
  "total": 2
}
```

**Business Rules**:
- Searches across name, email, and employee_id fields
- Case-insensitive partial matching
- Results ordered by name
- Performance target: < 200ms for 1,000 recipients

---

### GET /admin/recipients

List all recipients with filtering and pagination (Admin only).

**Access**: Admin, Super Admin

**Query Parameters**:
- `department` (optional): Filter by department
- `is_active` (optional): Filter by active status (true/false)
- `search` (optional): Search query
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 25, max: 100)

**Success Response** (200 OK):
```json
{
  "recipients": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "employee_id": "EMP001",
      "name": "Jane Doe",
      "email": "jane.doe@company.com",
      "department": "Engineering",
      "phone": "+1-555-0123",
      "location": "Building A",
      "is_active": true,
      "package_count": 15,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-15T14:00:00Z"
    }
  ],
  "total": 250,
  "skip": 0,
  "limit": 25,
  "has_more": true
}
```

---

### POST /admin/recipients/new

Create a new recipient (Admin only).

**Access**: Admin, Super Admin

**Request Body**:
```json
{
  "employee_id": "EMP001",
  "name": "Jane Doe",
  "email": "jane.doe@company.com",
  "department": "Engineering",
  "phone": "+1-555-0123",
  "location": "Building A"
}
```

**Success Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "employee_id": "EMP001",
  "name": "Jane Doe",
  "email": "jane.doe@company.com",
  "department": "Engineering",
  "phone": "+1-555-0123",
  "location": "Building A",
  "is_active": true,
  "created_at": "2024-01-15T14:00:00Z"
}
```

**Error Responses**:

**409 Conflict** - Duplicate employee_id:
```json
{
  "detail": "Recipient with employee_id 'EMP001' already exists"
}
```

**422 Unprocessable Entity** - Invalid email:
```json
{
  "detail": "Invalid email format"
}
```

---

### PUT /admin/recipients/{recipient_id}/edit

Update recipient information (Admin only).

**Access**: Admin, Super Admin

**Path Parameters**:
- `recipient_id` (required): UUID of the recipient

**Request Body**:
```json
{
  "name": "Jane M. Doe",
  "email": "jane.doe@company.com",
  "department": "Engineering",
  "phone": "+1-555-0123",
  "location": "Building A - Floor 3"
}
```

**Success Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "employee_id": "EMP001",
  "name": "Jane M. Doe",
  "email": "jane.doe@company.com",
  "department": "Engineering",
  "phone": "+1-555-0123",
  "location": "Building A - Floor 3",
  "is_active": true,
  "updated_at": "2024-01-15T15:00:00Z"
}
```

**Business Rules**:
- employee_id cannot be changed
- Email must be unique
- Changes are logged in audit trail

---

### POST /admin/recipients/{recipient_id}/deactivate

Deactivate a recipient (soft delete) (Admin only).

**Access**: Admin, Super Admin

**Path Parameters**:
- `recipient_id` (required): UUID of the recipient

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Recipient deactivated successfully"
}
```

**Error Responses**:

**400 Bad Request** - Has active packages:
```json
{
  "detail": "Cannot deactivate recipient with active packages. Please resolve all packages first."
}
```

**Business Rules**:
- Cannot deactivate recipient with packages in status: registered, awaiting_pickup, out_for_delivery
- Deactivation is reversible (can be reactivated)
- Deactivated recipients don't appear in autocomplete

---

### POST /admin/recipients/import

Bulk import recipients from CSV file (Admin only).

**Access**: Admin, Super Admin

**Request**: `multipart/form-data`
- `file` (required): CSV file with headers: employee_id, name, email, department, phone, location
- `dry_run` (optional): Preview import without saving (default: false)

**CSV Format**:
```csv
employee_id,name,email,department,phone,location
EMP001,Jane Doe,jane.doe@company.com,Engineering,+1-555-0123,Building A
EMP002,Bob Smith,bob.smith@company.com,Marketing,+1-555-0124,Building B
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "summary": {
    "total_rows": 100,
    "created": 75,
    "updated": 20,
    "skipped": 3,
    "errors": 2
  },
  "errors": [
    {
      "row": 5,
      "employee_id": "EMP005",
      "error": "Invalid email format: 'invalid-email'"
    },
    {
      "row": 12,
      "employee_id": "EMP012",
      "error": "Missing required field: name"
    }
  ],
  "skipped": [
    {
      "row": 8,
      "employee_id": "EMP008",
      "reason": "No changes detected"
    }
  ]
}
```

**Dry Run Response** (200 OK):
```json
{
  "dry_run": true,
  "preview": {
    "total_rows": 100,
    "will_create": 75,
    "will_update": 20,
    "will_skip": 3,
    "will_error": 2
  },
  "sample_changes": [
    {
      "row": 1,
      "action": "create",
      "employee_id": "EMP001",
      "name": "Jane Doe"
    },
    {
      "row": 15,
      "action": "update",
      "employee_id": "EMP015",
      "changes": {
        "department": "Engineering → Marketing",
        "location": "Building A → Building B"
      }
    }
  ],
  "errors": [...]
}
```

**Error Responses**:

**400 Bad Request** - Invalid CSV format:
```json
{
  "detail": "Invalid CSV format. Missing required headers: employee_id, name, email"
}
```

**413 Payload Too Large** - File too large:
```json
{
  "detail": "CSV file exceeds maximum size of 10MB"
}
```

**Business Rules**:
- Duplicate employee_id triggers update instead of error
- Empty rows are skipped
- Maximum 10,000 rows per import
- Import is transactional (all or nothing unless errors)
- Dry run mode allows preview before committing
- Import activity is logged in audit trail

---

## User Management Endpoints

### GET /users

List all users (Admin only).

**Query Parameters**:
- `role` (optional): Filter by role (operator, admin, super_admin)
- `is_active` (optional): Filter by active status (true/false)
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100)

**Response** (200 OK):
```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john.smith",
      "email": "john.smith@company.com",
      "full_name": "John Smith",
      "role": "operator",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

---

### GET /users/{user_id}

Get details of a specific user (Admin only).

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.smith",
  "email": "john.smith@company.com",
  "full_name": "John Smith",
  "role": "operator",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-15T14:20:00Z"
}
```

---

### POST /users

Create a new user (Admin only).

**Request**:
```json
{
  "username": "jane.doe",
  "email": "jane.doe@company.com",
  "full_name": "Jane Doe",
  "password": "SecurePassword123!",
  "role": "operator"
}
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "username": "jane.doe",
  "email": "jane.doe@company.com",
  "full_name": "Jane Doe",
  "role": "operator",
  "is_active": true,
  "created_at": "2024-01-15T15:00:00Z"
}
```

---

### PUT /users/{user_id}

Update user information (Admin only).

**Request**:
```json
{
  "email": "jane.doe@company.com",
  "full_name": "Jane M. Doe",
  "role": "admin",
  "is_active": true
}
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "username": "jane.doe",
  "email": "jane.doe@company.com",
  "full_name": "Jane M. Doe",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-15T15:00:00Z"
}
```

---

### DELETE /users/{user_id}

Delete a user (Super Admin only).

**Response** (200 OK):
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

### PUT /users/{user_id}/password

Change user password (Admin can change any user, users can change their own).

**Request**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

---

## Dashboard Endpoints

### GET /dashboard

Get dashboard statistics and recent activity.

**Access**: All authenticated users

**Query Parameters**:
- `period` (optional): Time period for statistics (today, week, month, year) - default: today

**Success Response** (200 OK):
```json
{
  "statistics": {
    "registered_today": 12,
    "awaiting_pickup": 45,
    "delivered_today": 8,
    "total_active": 57
  },
  "packages_by_status": {
    "registered": 12,
    "awaiting_pickup": 45,
    "out_for_delivery": 3,
    "delivered": 8,
    "returned": 1
  },
  "packages_by_carrier": {
    "UPS": 25,
    "FedEx": 20,
    "USPS": 10,
    "DHL": 2
  },
  "top_recipients": [
    {
      "recipient_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Jane Doe",
      "department": "Engineering",
      "package_count": 15
    },
    {
      "recipient_id": "550e8400-e29b-41d4-a716-446655440011",
      "name": "Bob Smith",
      "department": "Marketing",
      "package_count": 12
    }
  ],
  "recent_packages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "tracking_no": "1Z999AA10123456784",
      "carrier": "UPS",
      "recipient_name": "Jane Doe",
      "status": "awaiting_pickup",
      "created_at": "2024-01-15T14:30:00Z"
    }
  ],
  "period": "today",
  "generated_at": "2024-01-15T16:00:00Z"
}
```

**Performance**: Response time < 200ms with caching (1 minute TTL)

---

## Reports & Analytics Endpoints

### GET /admin/reports/summary

Get detailed summary statistics for reporting (Admin only).

**Access**: Admin, Super Admin

**Query Parameters**:
- `start_date` (optional): Start date for filtering (ISO 8601 format) - default: 30 days ago
- `end_date` (optional): End date for filtering (ISO 8601 format) - default: today
- `group_by` (optional): Grouping dimension (day, week, month) - default: day

**Success Response** (200 OK):
```json
{
  "summary": {
    "total_packages": 150,
    "registered": 12,
    "awaiting_pickup": 45,
    "out_for_delivery": 3,
    "delivered": 85,
    "returned": 5
  },
  "packages_by_carrier": {
    "UPS": 60,
    "FedEx": 50,
    "USPS": 30,
    "DHL": 10
  },
  "packages_by_department": {
    "Engineering": 45,
    "Marketing": 30,
    "Sales": 25,
    "Operations": 20,
    "Other": 30
  },
  "performance_metrics": {
    "average_registration_to_pickup_hours": 4.5,
    "average_registration_to_delivery_hours": 24.2,
    "pickup_rate_percentage": 95.3,
    "return_rate_percentage": 3.3
  },
  "trend_data": [
    {
      "date": "2024-01-01",
      "registered": 5,
      "delivered": 3
    },
    {
      "date": "2024-01-02",
      "registered": 8,
      "delivered": 6
    }
  ],
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "generated_at": "2024-01-31T16:00:00Z"
}
```

---

### GET /admin/reports/export

Export package data in CSV or JSON format (Admin only).

**Access**: Admin, Super Admin

**Query Parameters**:
- `format` (required): Export format (csv, json)
- `status` (optional): Filter by status
- `carrier` (optional): Filter by carrier
- `department` (optional): Filter by recipient department
- `start_date` (optional): Start date for filtering (ISO 8601 format)
- `end_date` (optional): End date for filtering (ISO 8601 format)

**Example Request**:
```
GET /admin/reports/export?format=csv&status=delivered&start_date=2024-01-01&end_date=2024-01-31
```

**Success Response** (200 OK):

**CSV Format**:
```
Content-Type: text/csv
Content-Disposition: attachment; filename="packages-export-20240131.csv"

id,tracking_no,carrier,recipient_name,recipient_email,department,status,notes,created_at,updated_at
550e8400-e29b-41d4-a716-446655440001,1Z999AA10123456784,UPS,Jane Doe,jane.doe@company.com,Engineering,delivered,Handle with care,2024-01-15T14:30:00Z,2024-01-15T16:45:00Z
```

**JSON Format**:
```json
{
  "export_date": "2024-01-31T16:00:00Z",
  "filters": {
    "status": "delivered",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "total_records": 85,
  "packages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "tracking_no": "1Z999AA10123456784",
      "carrier": "UPS",
      "recipient": {
        "employee_id": "EMP001",
        "name": "Jane Doe",
        "email": "jane.doe@company.com",
        "department": "Engineering"
      },
      "status": "delivered",
      "notes": "Handle with care",
      "created_by": "john.operator",
      "created_at": "2024-01-15T14:30:00Z",
      "updated_at": "2024-01-15T16:45:00Z",
      "timeline": [
        {
          "status": "registered",
          "timestamp": "2024-01-15T14:30:00Z",
          "actor": "john.operator"
        },
        {
          "status": "awaiting_pickup",
          "timestamp": "2024-01-15T15:00:00Z",
          "actor": "john.operator"
        },
        {
          "status": "delivered",
          "timestamp": "2024-01-15T16:45:00Z",
          "actor": "jane.operator"
        }
      ]
    }
  ]
}
```

**Business Rules**:
- Maximum 10,000 records per export
- Large exports may take several seconds
- Export activity is logged in audit trail

---

## Audit Log Endpoints

### GET /admin/audit-logs

Get audit log entries for security and compliance (Super Admin only).

**Access**: Super Admin only

**Query Parameters**:
- `user_id` (optional): Filter by specific user UUID
- `username` (optional): Filter by username (partial match)
- `event_type` (optional): Filter by event type
- `start_date` (optional): Start date for filtering (ISO 8601 format)
- `end_date` (optional): End date for filtering (ISO 8601 format)
- `ip_address` (optional): Filter by IP address
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100, max: 1000)

**Event Types**:
- `login` - Successful login
- `logout` - User logout
- `login_failed` - Failed login attempt
- `password_changed` - Password change
- `password_reset` - Admin password reset
- `user_created` - New user account created
- `user_updated` - User account modified
- `user_deactivated` - User account deactivated
- `account_locked` - Account locked due to failed attempts
- `account_unlocked` - Account unlocked by admin
- `package_created` - Package registered
- `package_updated` - Package modified
- `package_status_changed` - Package status updated
- `recipient_created` - Recipient added
- `recipient_updated` - Recipient modified
- `recipient_imported` - Bulk recipient import
- `export_generated` - Report exported

**Example Request**:
```
GET /admin/audit-logs?event_type=login_failed&start_date=2024-01-01&limit=50
```

**Success Response** (200 OK):
```json
{
  "logs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john.operator",
      "event_type": "package_created",
      "details": {
        "package_id": "550e8400-e29b-41d4-a716-446655440001",
        "tracking_no": "1Z999AA10123456784",
        "recipient_name": "Jane Doe",
        "carrier": "UPS"
      },
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "created_at": "2024-01-15T14:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "user_id": null,
      "username": "invalid.user",
      "event_type": "login_failed",
      "details": {
        "reason": "Invalid credentials",
        "attempt_count": 3
      },
      "ip_address": "192.168.1.105",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "created_at": "2024-01-15T14:25:00Z"
    }
  ],
  "total": 1247,
  "skip": 0,
  "limit": 100,
  "has_more": true
}
```

**Business Rules**:
- All authentication events are logged
- Failed login attempts include attempted username
- Logs are retained for minimum 365 days
- Logs are immutable (cannot be modified or deleted)
- Only Super Admin can access audit logs
- Sensitive data (passwords) is never logged

---

## Health & Status

### GET /health

Health check endpoint (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00Z",
  "version": "1.0.0",
  "database": "connected"
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Authentication endpoints: 5 requests per minute per IP
- General endpoints: 100 requests per minute per user
- Import endpoints: 10 requests per hour per user

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642258800
```

---

## CSRF Protection

All state-changing requests (POST, PUT, DELETE) require a valid CSRF token:
1. Token is automatically included in forms rendered by the server
2. For API calls, retrieve token from cookie `csrf_token`
3. Include token in request header: `X-CSRF-Token: <token>`

---

## Pagination

List endpoints support pagination with consistent parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

Response includes pagination metadata:
```json
{
  "data": [...],
  "total": 250,
  "skip": 0,
  "limit": 100
}
```

---

## Filtering & Sorting

List endpoints support filtering and sorting:

**Filtering**: Use query parameters matching field names
```
GET /packages?status=pending&carrier=FedEx
```

**Sorting**: Use `sort` parameter with field name and direction
```
GET /packages?sort=received_date:desc
```

---

## WebSocket Support

Real-time updates are available via WebSocket connection:

**Endpoint**: `wss://mailroom.company.local/ws`

**Authentication**: Include session cookie in connection request

**Message Format**:
```json
{
  "type": "package_update",
  "action": "created",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "tracking_number": "TRK-2024-001",
    "status": "pending"
  }
}
```

**Event Types**:
- `package_created`: New package added
- `package_updated`: Package information changed
- `package_picked_up`: Package marked as picked up
- `package_deleted`: Package removed

---

## API Versioning

Current API version: `v1`

Version is included in response headers:
```
X-API-Version: 1.0.0
```

Breaking changes will be introduced in new versions with appropriate deprecation notices.

---

## Support

For API support and questions:
- Email: support@company.com
- Documentation: https://mailroom.company.local/docs
- Interactive API docs: https://mailroom.company.local/docs
