# AI Product Design Prompt - Mailroom Tracking MVP

This file is a cleaned, retained product-planning prompt for the Mailroom Tracking application.

## Role

You are an AI product designer and technical planner. Produce a complete Product Requirements Document (PRD) and Design Specification for an internal Mailroom Tracking web application MVP.

## Project Overview

- Internal web app behind a corporate firewall
- Windows Server deployment
- Python with FastAPI
- SQLite as the local application database
- Mobile-friendly for tablet and phone use by mailroom staff
- Username and password authentication only

## System Objectives

1. Track incoming packages and internal mail.
2. Maintain chain-of-custody visibility until delivery or pickup.
3. Let admins manage users and recipients.
4. Provide dashboards and exports.
5. Operate fully offline inside the internal network.

## Roles

| Role | Description | Permissions |
|---|---|---|
| Super Admin | System owner | Full access to users, configuration, and data |
| Admin | Mailroom administrator | Manage operators, recipients, and reports |
| Operator | Frontline mailroom staff | Register packages, update status, upload attachments |

## Core MVP Scope

### Authentication and roles

- Username and password login
- Argon2id password hashing
- Session management with secure cookies
- Role-based access control
- Password reset and forced password change flows
- Account lockout after repeated failures

### User management

- Create, edit, and deactivate users
- Assign roles
- Reset passwords
- Record audit events

### Recipient management

- Manual CRUD
- CSV import with validation
- Search by name, email, or employee ID

### Package tracking

- Register package
- Link package to recipient
- Track lifecycle through status changes
- Upload supporting images
- Generate QR code links to package detail pages

### Reporting

- Dashboard summaries
- CSV export
- Audit visibility

## Data Model Expectations

Core tables:

- `users`
- `sessions`
- `auth_events`
- `recipients`
- `packages`
- `package_events`
- `attachments`
- `system_settings`

## Technical Constraints

| Component | Expected technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Jinja2, HTMX |
| Frontend | TailwindCSS, daisyUI, HTMX |
| Database | SQLite |
| Deployment | Windows Service plus reverse proxy |
| Storage | Local NTFS for uploads |
| Security | HTTPS, CSRF, rate limiting, role enforcement |
| Testing | Pytest-based automated coverage |

## UI and UX Requirements

- Mobile-first responsive layouts
- Large touch-friendly controls
- Fast search flows for operators
- Clear status color coding
- Minimal friction for scanning QR stickers and updating a package

## Non-Functional Requirements

- Fast response times on LAN
- Durable local persistence
- Operationally simple backups
- Clear environment-based configuration
- Suitable for roughly 10 to 20 concurrent operators

## Deliverables Required

Produce the following in Markdown:

1. PRD
2. Functional design specification
3. ERD
4. User flows
5. Wireframe descriptions
6. Configuration table
7. MVP readiness checklist
8. Phase 2 roadmap

## Output Structure

```text
# Mailroom Tracking MVP - Product Requirements and Design
## 1. Overview
## 2. Goals and Constraints
## 3. Roles and Permissions
## 4. Functional Requirements
## 5. Data Design
## 6. UI and UX Design
## 7. System Architecture
## 8. Non-Functional Requirements
## 9. MVP Readiness Checklist
## 10. Phase 2 Recommendations
```

## Note

Treat this file as a planning prompt artifact. For the current implemented system, prefer the root `README.md` and the docs under `docs/`.
