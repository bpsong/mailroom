# Super Administrator User Guide

## Introduction

The Super Administrator owns the Mailroom Tracking System. Use this guide to install the application, configure QR features, manage users, and keep the platform secure and healthy.

## Responsibilities

- **Initial setup** - Install services, bootstrap the database, set baseline configuration.
- **Account governance** - Create and manage Super Admin, Admin, and Operator accounts.
- **Security** - Review audit logs, enforce password policies, and respond to incidents.
- **Configuration** - Maintain `.env` values plus in-app settings such as the QR code base URL.
- **Data protection** - Schedule backups, perform restore drills, and document results.
- **Operations** - Monitor logs, run database maintenance, and verify scheduled jobs.
- **Support** - Provide Tier 2 help for admins/operators and coordinate with IT.

---

## Initial System Setup

### First-Time Installation

1. Install Python dependencies (`pip install -r requirements.txt` or `uv pip install .`).
2. Place the project under `C:\MailroomApp` (or another controlled directory).
3. Configure the process supervisor (NSSM, systemd, etc.) to run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Configure the reverse proxy (Caddy) for HTTPS termination.
5. Copy `.env.example` to `.env` and update the values shown in the Configuration section.

### Default Credentials

- Username: `admin`
- Password: Defined during installation (environment variable or bootstrap script).

Change this password immediately after the first login and store the new value in a password manager.

### Initial Checklist

1. **Log in with the bootstrap account.**
2. **Change the Super Admin password.**
   - Click your profile avatar -> Change Password.
   - Enter the old password once and a strong replacement twice.
   - Log out and back in to verify.
3. **Create a backup Super Admin.**
   - Go to Admin -> Users -> New User.
   - Assign the `super_admin` role and enable "Force password change".
4. **Review `.env` and restart the service.**
   - Confirm host/port, log paths, DuckDB file, and rate limits.
5. **Configure the QR Code Base URL (new).**
   - Open Admin -> System Settings.
   - Enter the production host that operators will use when scanning stickers (for example, `https://mailroom.company.local`).
   - Click Save. The value must start with `http://` or `https://`. Every QR sticker uses this base URL when generating the package detail link.
6. **Set up automated backups.**
   - Use the scripts in `scripts/` or Task Scheduler.
   - Store backups on a different drive or secure network share.
   - Test at least one restore before launch.
7. **Import recipients.**
   - Prepare a CSV with columns `employee_id,name,email,department`.
   - Navigate to Recipients -> Import CSV and follow the wizard.
8. **Create operator accounts.**
   - Go to Admin -> Users -> New User.
   - Assign the `operator` role, provide a temporary password, and require a forced change.
9. **Perform a smoke test.**
   - Register a package, upload a photo, print the QR sticker, scan it on a mobile device, and walk the package through one full lifecycle.

---

## User Management

### Roles

| Role        | Capabilities                                                                           |
|-------------|----------------------------------------------------------------------------------------|
| Super Admin | Manage configuration, users, audit logs, backups, QR settings, and system maintenance. |
| Admin       | Manage operators and recipients, register packages, run reports.                       |
| Operator    | Register packages, update statuses, capture photos, use QR code actions.               |

### Creating Users

1. Go to **Admin -> Users -> New User**.
2. Provide username, full name, and optional contact details.
3. Select the appropriate role.
4. Enter a temporary password and keep **Force password change** enabled.
5. Click **Create User** and deliver the credentials securely.

### Editing and Deactivating

- **Edit:** Find the user, click **Edit**, adjust fields, and save.
- **Deactivate:** Open the user profile, click **Deactivate User**, provide a reason, and confirm. The account loses access immediately and active sessions are revoked.

### Password Resets

1. Open the user record.
2. Click **Reset Password**.
3. Provide a temporary password and keep **Force password change** checked.
4. Communicate the temporary password out-of-band.

### Audit Logs

- Navigate to **Admin -> Audit Log**.
- Filter by user, action, or date.
- QR-related events appear as `system_settings_change` with details such as `qr_base_url_created` or `qr_base_url_updated`.

---

## QR Code Operations

### Generation

- `QRCodeService` encodes the package detail URL using the configured base URL (or the request host if no value is set).
- Output is 2 cm by 2 cm at 300 DPI with high error correction (`ERROR_CORRECT_H`).

### Download Workflow

1. From the package list or detail page, open the **QR Actions** dropdown.
2. Click **Download QR Code** to fetch `qr_code_{package_id}.png`.
3. Use the file for offline archiving or bulk label sheets.

### Print Workflow

1. Choose **QR Actions -> Print QR Code**.
2. A new tab loads `templates/packages/qrcode_print.html`.
3. Confirm the preview shows only the QR image and tracking number.
4. Click **Print QR Code** (calls `window.print()`) and send to the label printer.

### Mobile Scanning Flow

1. Operators attach the sticker to the package.
2. When someone scans the QR code, the browser loads `/packages/{id}` on the configured host.
3. Unauthenticated users are redirected to `/auth/login?next=...`.
4. After login, the user lands directly on the package detail page and can update the status immediately.

### Troubleshooting

| Problem                                  | Resolution                                                                 |
|------------------------------------------|---------------------------------------------------------------------------|
| QR sticker points to localhost           | Update the QR base URL in **Admin -> System Settings** and reprint.       |
| Sticker prints at the wrong size         | Disable "Fit to page" in the print dialog; confirm printer DPI settings.  |
| Browser shows blank print page           | Verify the package exists and check browser console for CSP violations.   |
| Scanner cannot reach the host            | Confirm DNS/SSL for the configured base URL and verify the device VPN.    |

---

## System Configuration

### Environment Variables

`C:\MailroomApp\.env`

```env
# Application
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=<generate a random 32 byte string>

# Database
DATABASE_PATH=./data/mailroom.duckdb
DATABASE_CHECKPOINT_INTERVAL=300

# Security
SESSION_TIMEOUT=1800
MAX_FAILED_LOGINS=5
ACCOUNT_LOCKOUT_DURATION=1800
PASSWORD_MIN_LENGTH=12
PASSWORD_HISTORY_COUNT=3

# File uploads
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=5242880
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/mailroom.log
LOG_RETENTION_DAYS=365
```

### QR Code Base URL Setting

- Stored in the `system_settings` table with key `qr_base_url`.
- Configured through **Admin -> System Settings** (Super Admin only).
- Validation: must start with `http://` or `https://`. Trailing slashes are removed.
- Every QR sticker uses this value to build `https://host/packages/{package_id}`.
- If not set, the backend falls back to `request.base_url`, which is acceptable for development but risky for production.

### Safe Configuration Changes

1. Backup the current `.env`.
2. Stop the service.
3. Apply edits.
4. Start the service and monitor `logs/mailroom.log`.
5. Verify the change in the UI or via `/health`.

---

## Monitoring and Maintenance

### Daily

- Check the dashboard for abnormal package counts.
- Review the audit log for failed logins or configuration changes.
- Confirm the latest backup job succeeded.

### Weekly

- Run DuckDB maintenance:
  ```powershell
  duckdb C:\MailroomApp\data\mailroom.duckdb "VACUUM; ANALYZE;"
  ```
- Archive or rotate `logs/mailroom.log` if it exceeds expected size.
- Validate that QR codes still resolve correctly by scanning a random sticker.

### Monthly

- Restore a backup to a staging environment as a disaster recovery rehearsal.
- Review certificates and DNS entries for expiration.
- Audit user accounts for leavers and deactivate stale accounts.

### Log Management

- **Path:** `C:\MailroomApp\logs\mailroom.log`
- Tail logs:
  ```powershell
  Get-Content C:\MailroomApp\logs\mailroom.log -Tail 100
  ```
- Search for errors:
  ```powershell
  Select-String -Path C:\MailroomApp\logs\mailroom.log -Pattern "ERROR"
  ```

### Health Endpoint

- `GET https://<host>/health`
- Returns JSON with `{"status": "healthy"}` when the app, database, and background tasks are operational.

---

## Backups and Recovery

### Backup Strategy

- Frequency: nightly full backup of `data/` and `uploads/`.
- Storage: secondary disk or secure network share with restricted access.
- Automation: Task Scheduler running the scripts in `scripts/`.

### Restore Checklist

1. Stop the Mailroom service.
2. Copy the backup DuckDB file and uploads directory into place.
3. Start the service.
4. Log in and confirm recent packages exist.

### Disaster Scenarios

| Scenario            | Action                                                                 |
|---------------------|------------------------------------------------------------------------|
| Hardware failure    | Restore to new hardware or VM, update DNS, and confirm QR base URL.    |
| Database corruption | Restore the most recent good backup, investigate root cause.          |
| Security breach     | Disable affected accounts, rotate credentials, restore clean backup.  |

---

## Security and Compliance

- Enforce least privilege: operators should not receive admin rights.
- Require password changes for new accounts and lock accounts after 5 failures.
- Review `auth_events` and `system_settings_change` logs weekly.
- Document every emergency change (date, reason, approver).
- Keep the OS, Python runtime, and dependencies patched.

---

## Troubleshooting

### Users Cannot Log In

1. Confirm the Mailroom process is running.
2. Check for lockout entries in the audit log.
3. Reset the password and ensure the user receives the new value securely.
4. Verify reverse proxy/HTTPS configuration if all users fail.

### QR Codes Redirect to Wrong Host

1. Open **Admin -> System Settings**.
2. Update the QR base URL and save.
3. Reprint affected stickers.

### QR Print Page Blank

1. Ensure the package exists and the user has permission.
2. Check browser console for CSP violations.
3. Inspect `logs/mailroom.log` for QR generation errors.

### Database Locked

1. Make sure no DuckDB CLI sessions are open.
2. Confirm the async write queue worker is running.
3. Restart the service if locks persist.

### File Upload Fails

1. Verify `uploads/` directory permissions.
2. Confirm the file meets size/type rules.
3. Check disk space.

---

## Emergency Procedures

### System Down

1. Check Windows services (Mailroom, Caddy).
2. Review `mailroom.log`.
3. Restart the service.
4. If unresolved, restore from backup and escalate to IT.

### Data Loss

1. Stop writes immediately.
2. Restore the latest verified backup.
3. Notify stakeholders and document the incident.

### Security Breach

1. Disable compromised accounts and rotate Super Admin passwords.
2. Review audit logs for scope.
3. Engage the security team and follow the incident response plan.

---

## Support and Resources

- Technical docs: `docs/` (API, database schema, deployment, security).
- Requirements/design: `.kiro/specs/mailroom-tracking-mvp/`.
- Escalation: follow your internal on-call or IT contact list.

---

**Version:** 2.0 (QR code update)  
**Last Updated:** November 2025  
**Maintained By:** System Administrator
