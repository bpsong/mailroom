# ðŸ§  AI Product Design Prompt â€” Mailroom Tracking MVP

You are an **AI Product Designer and Technical System Planner**.  
Your job is to create a complete **Product Requirements Document (PRD)** and **Design Specification** for a new **Mailroom Tracking Web Application (MVP)**.

---

## ðŸ¢ Project Overview

This is an **internal web application** that will run **behind a corporate firewall** on a **Windows Server** using **Python (FastAPI)** and **SQLite** as the local database.  
It will help the companyâ€™s **mailroom team** register, track, and manage incoming and outgoing physical packages.

The app must be **mobile-friendly**, usable on tablets or phones by mailroom staff, and accessed only by authorized users via **username and password login**.

---

## ðŸŽ¯ System Objectives

1. Record and track all incoming mail and packages.
2. Manage the chain of custody until pickup or delivery.
3. Enable admins to manage operators and recipients.
4. Provide simple dashboards and reports.
5. Operate fully offline within an internal network (no external APIs).

---

## ðŸ‘¥ User Roles and Access

| Role | Description | Permissions |
|------|--------------|--------------|
| **Super Admin** | System owner who bootstraps the app. | Full access to all data, configuration, and users. |
| **Admin (Sub-admin)** | Oversees mailroom operations. | Manage operators, recipients, and view reports. Cannot delete or modify the super admin. |
| **Operator** | Frontline staff who handle mail and packages. | Register new packages, update status, upload photos/signatures. |

---

## ðŸ§© Core MVP Features

### 1. Authentication & Roles
- Username/password login (Argon2id or bcrypt hashing).
- Session management (secure cookies).
- Logout, timeout, and account lockout after repeated failures.
- Role-based access control (super_admin, admin, operator).
- Password policy: min 12 chars, mixed case/symbols, forced reset option.
- Admin can reset passwords for operators and other admins.
- Super_admin cannot be deactivated or modified by others.

---

### 2. User Management (Admin & Super Admin)
- Create, edit, and deactivate users.
- Assign/change user roles (admin/operator).
- Reset passwords or force â€œmust change password on next loginâ€.
- Audit log of user actions (created, updated, deactivated).
- Self password change for all users.

**Endpoints & Pages**
- `/admin/users` â€” list/search users.
- `/admin/users/new` â€” create user.
- `/admin/users/:id/edit` â€” edit details.
- `/admin/users/:id/deactivate` â€” toggle active.
- `/admin/users/:id/password` â€” reset password.
- `/me/password` â€” change own password.

---

### 3. Recipient Management
- Maintain a master list of employees who receive mail.
- **Import via CSV** (admin-only).
- Manual add/edit/deactivate.
- Searchable and autocompletable by name, email, or employee ID.

**Recipient Fields**
| Field | Type | Description |
|--------|------|-------------|
| `employee_id` | TEXT | Unique staff ID |
| `name` | TEXT | Full name |
| `email` | TEXT | Work email |
| `department` | TEXT | Department name |
| `phone` | TEXT | Optional contact number |
| `location` | TEXT | Floor or office location |
| `is_active` | BOOLEAN | Active/inactive status |

**Endpoints & Pages**
- `/admin/recipients` â€” list/search.
- `/admin/recipients/import` â€” upload CSV (with dry-run validation).
- `/admin/recipients/new` â€” add manually.
- `/admin/recipients/:id/edit` â€” edit existing recipient.
- `/recipients/search?q=` â€” used by operator form autocomplete.

**CSV Example**
```csv
employee_id,name,email,department,phone,location,is_active
E001,Jane Tan,jane.tan@company.com,Finance,91234567,Level 5,true
E002,Ahmad Rahim,ahmad.rahim@company.com,HR,92345678,Level 7,true
```

---

### 4. Package Registration & Tracking
Operators record each incoming mail/package.

**Workflow**
1. Operator logs in.
2. Registers a package (tracking number, courier, recipient, notes, photo).
3. Status starts as `Registered`.
4. Operator marks as `Awaiting Pickup`, `Out for Delivery`, `Delivered`, or `Returned`.
5. Status changes are logged as events with timestamps and actor IDs.

**Data captured**
| Field | Type | Description |
|--------|------|-------------|
| `tracking_no` | TEXT | Courier tracking number or internal ref |
| `carrier` | TEXT | DHL, SingPost, etc. |
| `recipient_id` | UUID | Link to recipient |
| `status` | TEXT | registered / awaiting_pickup / out_for_delivery / delivered / returned |
| `notes` | TEXT | Optional comments |
| `photo_path` | TEXT | Path to stored photo (if any) |
| `created_at` | TIMESTAMP | Auto-captured |
| `updated_at` | TIMESTAMP | Auto-captured |

---

### 5. Search & Filter
- Search by tracking number, recipient name, department, or status.
- Filters: date range, status, operator.
- Paginated list view.

---

### 6. Dashboard & Reports
- Admin dashboard with summary tiles:
  - Packages registered today
  - Packages awaiting pickup
  - Packages delivered / returned
  - Top recipients / departments
- CSV export of logs or daily summary.

---

### 7. Audit & Logging
- Track all important actions:
  - Logins, logouts, failed attempts.
  - User CRUD and password resets.
  - Recipient imports.
  - Package status updates.
- Logs stored in `auth_events` and `package_events` tables.
- System log file rotated weekly.

---

## ðŸ—‚ï¸ Database (SQLite)

Tables:
- `users`
- `sessions`
- `auth_events`
- `recipients`
- `packages`
- `package_events`
- `attachments`

All writes funnel through a single async writer task to avoid SQLite locking issues.

---

## ðŸ–¥ï¸ Technical Requirements

| Component | Technology / Spec |
|------------|-------------------|
| **Backend** | Python 3.12+, FastAPI, Jinja2, HTMX |
| **Frontend** | TailwindCSS + HTMX (responsive mobile-first) |
| **Database** | SQLite (single file `.sqlite3`) |
| **Auth** | Argon2id / bcrypt password hashing, secure session cookies |
| **Deployment** | Windows Service (via NSSM or WinSW) |
| **Reverse Proxy** | Caddy or IIS ARR (HTTPS) |
| **Storage** | Local NTFS folder for attachments/photos |
| **Backup** | Daily VSS snapshot of DB and attachments |
| **Security** | HTTPS, HttpOnly cookies, rate limit, CSRF tokens |
| **Testing** | Pytest + httpx for integration tests |

---

## ðŸ“± UI / UX Requirements

### Key Pages
1. Login
2. Dashboard
3. Package Registration
4. Package List / Search
5. Package Detail (timeline)
6. Recipient List / Import
7. User Management
8. Change Password
9. Reports

### UI Guidelines
- Responsive design (mobile/tablet first).
- Use large buttons for touchscreens.
- Color-coded package statuses.
- Quick search bar on top of all operator views.
- Light/dark mode optional.

---

## ðŸ”’ Security & Access Controls
- HTTPS enforced (LAN TLS certs).
- Only LAN/VPN IPs can connect.
- Session timeout: 30 minutes idle.
- Rate-limit login attempts.
- Password hashes never displayed.
- Role-based access enforcement at route level.

---

## ðŸ§® Non-Functional Requirements
- **Performance:** <200ms API response time (local LAN).
- **Scalability:** Support 10â€“20 concurrent operators.
- **Reliability:** Graceful restart and data durability (SQLite WAL/checkpoint).
- **Maintainability:** Configurable `.env` for ports, file paths, retention.
- **Backup Policy:** Nightly file copy + weekly verification restore test.

---

## ðŸ§  Deliverables Required from AI Assistant

Please generate the following documents in markdown format:

1. **Product Requirements Document (PRD)** â€” detailed feature specs, field validation rules, and acceptance criteria.
2. **Functional Design Specification (FDS)** â€” endpoints, data flow diagrams, and permission matrices.
3. **Entity Relationship Diagram (ERD)** â€” database schema overview.
4. **User Flow Diagrams** â€” for Operator, Admin, and Super Admin.
5. **Wireframe Descriptions** â€” for mobile and desktop layouts.
6. **Configuration Parameters Table** â€” password policy, timeout, retention, file paths.
7. **MVP Readiness Checklist** â€” items to confirm before deployment.
8. **Phase 2 Roadmap** â€” suggested future enhancements (notifications, QR scanning, analytics).

---

## ðŸª„ Output Format

Use this structure:

```
# Mailroom Tracking MVP â€” Product Requirements & Design

## 1. Overview
## 2. Goals & Constraints
## 3. Roles & Permissions
## 4. Functional Requirements
## 5. Data Design
## 6. UI/UX Design
## 7. System Architecture
## 8. Non-Functional Requirements
## 9. MVP Readiness Checklist
## 10. Phase 2 Recommendations
```

Each section should include tables, bullet points, and optional Mermaid diagrams (ERD, sequence, flow).

---

## âœï¸ Tone & Style

- Professional, clear, and complete.
- Structured for developers and managers to understand quickly.
- Include assumptions, constraints, and clear acceptance criteria.

---

**End of Prompt**


