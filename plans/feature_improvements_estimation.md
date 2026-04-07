# Mailroom Tracking System - Feature Improvements Estimation

**Date:** 2026-04-06  
**Based on:** Email conversation with Roy  
**Purpose:** Time estimation for AI agent implementation of requested improvements

---

## Executive Summary

This document provides detailed time estimates for implementing six key improvements to the Mailroom Tracking System, based on feedback from stakeholder Roy. The total estimated effort is **58.5 hours**, recommended to be delivered in three phases.

---

## Feature Requirements from Stakeholder

### 1. Intake and Barcode Scanning
- **Requirement:** Support handheld USB scanners for registering accountable mail/parcels
- **Selected Approach:** Option A - Keyboard wedge mode (scanner mimics keyboard input)
- **Rationale:** Keep system complexity low; operators position cursor on tracking field, scanner inputs characters + Enter to submit form

### 2. Automated Notifications
- **Requirement:** Send email notifications to clients when they have accountable mail/parcels
- **Considerations:** SMTP gateway integration, authentication support, UAT environment needed for testing

### 3. Real-time Signature Capture
- **Requirement:** Capture client signature when handing over accountable mail/parcels
- **Implementation:** Signature captured as image, new "signed" status, multiple images tied to packages

### 4. Proof of Delivery Generation
- **Requirement:** Capture signature, photos, names of person who signed, date/time of delivery
- **Current State:** Most data already captured except signature

### 5. End-of-Month Report Generation
- **Requirement:** Generate reports with signatures, names, dates/times for all shipments
- **Current State:** CSV export exists; signature image export needs evaluation

### 6. Outbound Mail/Package Tracking (Additional)
- **Requirement:** Track outbound packages delivered out of mailroom by users
- **Scope:** Simple recording of outbound mail/package movements

---

## Detailed Estimation by Feature

### Feature 1: Barcode Scanner Integration (Keyboard Wedge)
**Complexity:** Low | **Risk:** Low

| Subtask | Hours |
|---------|-------|
| Add scanner-mode input field with auto-focus and debounce logic | 1.5 |
| Implement enter-to-submit form behavior for scanner "Enter" keystroke | 1.0 |
| Add visual/audio feedback on successful scan | 1.0 |
| Handle duplicate scan detection and error UX | 1.0 |
| Testing with simulated scanner input | 1.0 |
| **Subtotal** | **5.5** |

**Files to Modify:**
- `templates/packages/register.html` - Add scanner input handling
- `static/js/` - Add scanner utility script

---

### Feature 2: Automated Email Notifications
**Complexity:** Medium-High | **Risk:** Medium

| Subtask | Hours |
|---------|-------|
| Add SMTP configuration to `app/config.py` and `.env.example` | 1.0 |
| Create `EmailNotificationService` with SMTP send capability | 2.5 |
| Design email templates (HTML + text) for delivery notifications | 2.0 |
| Integrate notification triggers into `PackageService.update_status()` | 1.5 |
| Add notification audit log table and logging | 1.5 |
| Add admin settings UI for SMTP configuration | 1.5 |
| Testing (SMTP auth, delivery, error handling) | 2.0 |
| **Subtotal** | **12.0** |

**Files to Create/Modify:**
- `app/services/email_notification_service.py` - New service
- `app/config.py` - Add SMTP settings
- `.env.example` - Add SMTP env vars
- `app/services/package_service.py` - Add notification triggers
- `templates/emails/` - New email templates directory
- `templates/admin/settings.html` - Add SMTP config section

---

### Feature 3: Real-time Signature Capture
**Complexity:** Medium | **Risk:** Medium

| Subtask | Hours |
|---------|-------|
| Create signature capture UI component (HTML5 canvas + JS) | 3.0 |
| Add signature metadata fields to database migration | 1.5 |
| Create `SignatureService` for save/retrieve operations | 1.5 |
| Integrate signature capture into status update flow ("signed" status) | 2.0 |
| Add signature display in package detail view | 1.0 |
| Testing (touch/stylus input, validation, edge cases) | 1.5 |
| **Subtotal** | **10.5** |

**Files to Create/Modify:**
- `app/services/signature_service.py` - New service
- `app/database/migrations/add_signature_fields.py` - New migration
- `templates/components/signatureCapture.html` - New component
- `templates/packages/detail.html` - Add signature display
- `app/models/attachment.py` - Extend for signature type

---

### Feature 4: Proof of Delivery (POD) Generation
**Complexity:** Medium | **Risk:** Medium

| Subtask | Hours |
|---------|-------|
| Create POD data aggregation service | 1.5 |
| Design POD template (HTML for print/PDF) | 2.0 |
| Implement PDF generation (using WeasyPrint or similar) | 2.0 |
| Add POD download endpoint in `app/routes/packages.py` | 1.0 |
| Add POD generation trigger on "delivered"/"signed" status | 1.0 |
| Testing (PDF output, data accuracy, formatting) | 1.5 |
| **Subtotal** | **9.0** |

**Files to Create/Modify:**
- `app/services/pod_service.py` - New service
- `templates/pod/` - New POD template directory
- `app/routes/packages.py` - Add POD download route
- `pyproject.toml` - Add PDF generation dependency

---

### Feature 5: End-of-Month Report with Signatures
**Complexity:** Medium | **Risk:** Low-Medium

| Subtask | Hours |
|---------|-------|
| Enhance `ExportService` to include signature fields in CSV | 1.5 |
| Add date-range filter for monthly selection | 1.0 |
| Create monthly report summary view in admin | 1.5 |
| Add signature image export (optional - ZIP of images) | 2.0 |
| Add report archival/naming convention | 1.0 |
| Testing (large datasets, signature links, export integrity) | 1.5 |
| **Subtotal** | **8.5** |

**Files to Modify:**
- `app/services/export_service.py` - Add signature fields
- `app/routes/admin/reports.py` - Add monthly report endpoint
- `templates/admin/reports.html` - Add monthly report UI

---

### Feature 6: Outbound Mail/Package Tracking
**Complexity:** High | **Risk:** Medium-High

| Subtask | Hours |
|---------|-------|
| Database migration: add `direction` field + outbound-specific columns | 1.5 |
| Update `PackageService` to handle outbound creation/statuses | 2.5 |
| Create outbound registration form/template | 2.5 |
| Add outbound-specific status workflow | 1.5 |
| Update dashboard to show inbound vs outbound counts | 1.5 |
| Add outbound filtering in admin reports | 1.0 |
| Testing (outbound lifecycle, reporting, edge cases) | 2.5 |
| **Subtotal** | **13.0** |

**Files to Create/Modify:**
- `app/database/migrations/add_outbound_tracking.py` - New migration
- `app/models/package.py` - Add direction field
- `app/services/package_service.py` - Add outbound logic
- `templates/packages/outbound_register.html` - New template
- `app/routes/packages.py` - Add outbound routes
- `app/services/dashboard_service.py` - Add outbound metrics

---

## Total Estimation Summary

| Feature | Hours | Risk Level | Dependencies |
|---------|-------|------------|--------------|
| 1. Barcode Scanner Integration | 5.5 | Low | None |
| 2. Automated Email Notifications | 12.0 | Medium | SMTP access, UAT env |
| 3. Real-time Signature Capture | 10.5 | Medium | File service (exists) |
| 4. Proof of Delivery Generation | 9.0 | Medium | Feature 3 (signatures) |
| 5. End-of-Month Report with Signatures | 8.5 | Low-Medium | Feature 3 (signatures) |
| 6. Outbound Mail/Package Tracking | 13.0 | Medium-High | Schema changes |
| **TOTAL** | **58.5** | | |

---

## Recommended Implementation Phases

### Phase 1: Foundation & Operations (Week 1-2)
**Features:** Barcode Scanner + Outbound Tracking  
**Duration:** ~18.5 hours  
**Rationale:** Core operational improvements with low risk; establishes data model extensions

### Phase 2: Customer-Facing Features (Week 2-3)
**Features:** Email Notifications + Signature Capture  
**Duration:** ~22.5 hours  
**Rationale:** Requires UAT environment and stakeholder validation; builds on Phase 1

### Phase 3: Reporting & Compliance (Week 3-4)
**Features:** POD Generation + Monthly Reports  
**Duration:** ~17.5 hours  
**Rationale:** Dependent on Phase 2 signature capability; completes compliance requirements

---

## Current Codebase Assessment

### Ready Foundations
- Inbound package lifecycle (registration, status updates, events)
- Image upload pipeline (FileService with MIME validation)
- Timeline events and audit logging
- QR code generation and printing
- Admin CSV reporting with filtering

### Missing Capabilities
- Email/SMTP notification subsystem
- Signature capture domain model and UI
- PDF document generation
- Outbound package tracking
- Signature-inclusive reporting

### Architecture Fit
Current service-layer structure is clean and modular. New features can be added incrementally without major refactoring:
- New services can follow existing patterns in `app/services/`
- Schema migrations can extend existing tables
- Routes can be added to existing route modules
- Templates can extend current base layout

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Email deliverability issues | Medium | Use mock SMTP for development; test with real provider in UAT |
| Signature UX varies by device | Medium | Responsive canvas testing; fallback to file upload |
| Outbound complexity reveals schema limitations | Medium-High | Iterative schema design; direction field before separate entity |
| SMTP authentication requirements | Medium | Support multiple auth methods; document configuration |
| Barcode scanner hardware availability | Low | Simulate keyboard input for development; test with hardware before deployment |

---

## Prerequisites for Implementation

1. **Development Environment:** Python 3.13, DuckDB, existing project dependencies
2. **UAT Environment:** Required for email notification testing
3. **SMTP Credentials:** For email notification development and testing
4. **Barcode Scanner:** For Option A validation (can simulate initially)
5. **PDF Library:** WeasyPrint or similar for POD generation (new dependency)

---

## Appendix: Email Context

The estimation is based on the following requirements from Roy's feedback:

> 1. Intake and barcode scanning using handheld scanners for registering the accountable mail / parcel
> 2. Automated Notifications – sending email to notify client that they have an accountable mail / parcel
> 3. Real time signature capture for client to acknowledge that accountable mail / parcel has been handed over
> 4. Generation of Proof of Delivery - Capture Signature, Photos, Names of person that signed for the accountable mail / parcel, Date and Time of delivery
> 5. End of month generation of report for all shipments with Signature, Names of person that signed for the accountable mail / parcel, Date and Time of delivery
> 6. Simple outbound mail/package tracking, just to record which user ask mailroom to deliver package / mail out of mailroom
