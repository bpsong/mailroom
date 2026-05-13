# Super Administrator User Guide

## Who This Guide Is For

This guide is for the person or team that owns the Mailroom Tracking System for the organisation. In many mailrooms, this may be a mailroom manager, facilities manager, operations lead, or authorised senior administrator.

The guide is written for non-technical staff. It focuses on decisions, checks, and handoffs. If a task requires server access, database work, certificates, networking, or backups, coordinate with IT or your approved technical support team.

As a **Super Administrator**, you can:
- Manage all user roles, including Administrators and Operators.
- Maintain system settings available inside the application.
- Review audit logs and important activity.
- Oversee recipient data quality and reporting.
- Coordinate with IT for backups, system availability, and technical incidents.
- Set the operating rules for how the mailroom uses the system.

## Role Overview

| Role | Main Responsibility |
|------|---------------------|
| Operator | Registers packages, updates statuses, scans QR stickers, and delivers or releases items. |
| Administrator | Manages operators, recipients, imports, and reports for daily mailroom operations. |
| Super Administrator | Owns system access, settings, audit oversight, escalation, and governance. |

Super Administrator access should be limited to a small number of trusted people.

## First-Time Setup Checklist

Use this checklist when the system is first launched or handed over to a new mailroom owner.

1. **Confirm the system address**
   - Confirm the web address staff will use.
   - Confirm the address works from mailroom computers, tablets, and approved mobile devices.

2. **Change the initial Super Administrator password**
   - Log in with the initial account.
   - Change the password immediately.
   - Store emergency access details according to your organisation's policy.

3. **Create at least one backup Super Administrator**
   - Create a second trusted Super Administrator account.
   - Keep the number of Super Administrators small.
   - Make sure each person uses their own account.

4. **Set up Administrators and Operators**
   - Create Administrator accounts for mailroom supervisors or leads.
   - Create Operator accounts for daily mailroom staff.
   - Require users to change temporary passwords on first login.

5. **Confirm recipient data**
   - Import or review the staff recipient list.
   - Spot-check departments, locations, and email addresses.
   - Agree who will keep the list current.

6. **Confirm QR code settings**
   - Open **System Settings**.
   - Confirm the QR code base URL is the address staff should reach when scanning stickers.
   - Ask IT for help if you are unsure which address to use.

7. **Run an end-to-end mailroom test**
   - Register a test package.
   - Add a photo.
   - Print or scan the QR sticker if used.
   - Move the package through the normal statuses.
   - Confirm reports show the activity correctly.

8. **Confirm support and escalation**
   - Identify who handles user questions.
   - Identify who handles technical outages.
   - Identify who handles missing package or security incidents.

## Managing Roles and Access

### Create a User

1. Go to **Users**.
2. Click **Add New User**.
3. Enter the username and full name.
4. Choose the correct role:
   - **Operator** for daily package handling.
   - **Administrator** for supervisors who manage users, recipients, and reports.
   - **Super Administrator** only for authorised system owners.
5. Enter a temporary password.
6. Keep the first-login password change option enabled.
7. Click **Create User**.
8. Share credentials using an approved secure method.

### Edit a User

1. Go to **Users**.
2. Find the user.
3. Click **Edit**.
4. Update allowed details.
5. Click **Save Changes**.

Avoid changing someone's role unless the business reason is clear.

### Deactivate a User

Deactivate access when a person leaves, changes role, or no longer needs the system.

1. Go to **Users**.
2. Find the user.
3. Click **Deactivate**.
4. Confirm the action.

Past package activity remains in the system for reporting and audit history.

### Password Resets

1. Open the user's record.
2. Click **Reset Password**.
3. Enter a temporary password.
4. Require the user to change it at next login.
5. Share the temporary password securely.

If an account may have been misused, reset the password and review audit activity.

## System Settings

System settings affect how the application behaves for the mailroom team. Change them carefully and document important changes.

### QR Code Base URL

The QR code base URL controls where QR stickers send users when scanned.

Use the organisation-approved Mailroom Tracking System address, such as:

```text
https://mailroom.company.local
```

To update it:

1. Open **System Settings**.
2. Find **QR Code Base URL**.
3. Enter the correct system address.
4. Save the setting.
5. Print and scan a test QR sticker.

If QR stickers open the wrong page, show a security warning, or point to a local test address, contact IT and update this setting before printing more stickers.

### Change Control

For important settings:
- Record what changed.
- Record who approved it.
- Record when it changed.
- Test the system after the change.

## Audit Logs

Audit logs show important activity in the system, such as user changes, login events, and system setting changes.

### Review Audit Logs

1. Open **Audit Log**.
2. Filter by user, action, or date.
3. Review unusual or important events.

Look for:
- Repeated failed login attempts.
- Unexpected password resets.
- New administrator or Super Administrator accounts.
- Deactivated accounts.
- System setting changes.
- Unusual activity around a missing or disputed package.

Audit logs should be used to understand what happened, not to guess. If the issue is serious, involve IT, Security, HR, or management according to your organisation's process.

## Recipient Data Oversight

Accurate recipient information is essential in an enterprise mailroom.

As Super Administrator, make sure there is a clear owner for recipient updates. This may be:
- HR.
- Facilities.
- Department coordinators.
- Mailroom administration.

### Good Recipient Data Standards

Each active recipient should have:
- Correct full name.
- Employee or staff ID.
- Work email address.
- Department.
- Delivery location, such as building, floor, office, desk area, or mail stop.
- Phone or extension if used by the mailroom.

Set a regular schedule for updates, such as weekly or monthly, depending on staff movement.

## Reports and Operational Oversight

Use reports to monitor service levels and identify problems early.

Common checks:
- Packages still awaiting pickup from previous days.
- Packages out for delivery but not marked delivered.
- High-volume departments.
- Operators with unusually low or high activity.
- Recipients or locations with repeated delivery issues.
- Returned or exception items.

Reports may contain personal or business information. Store exports only in approved locations and share them only with people who need them.

## Daily, Weekly, and Monthly Checks

### Daily

- Check dashboard totals for unusual changes.
- Review old **Awaiting Pickup** items.
- Confirm critical mailroom staff can log in.
- Watch for repeated failed logins or access issues.

### Weekly

- Review recent audit activity.
- Check whether any users should be deactivated.
- Confirm recipient updates have been received or imported.
- Spot-check QR stickers by scanning one or two current packages.

### Monthly

- Review all Administrator and Super Administrator accounts.
- Confirm backup completion with IT or technical support.
- Export required mailroom activity reports.
- Review recurring delivery delays with the mailroom team.
- Confirm the support and escalation contact list is current.

## Backups and Recovery

Backups are usually handled by IT or technical support, but the Super Administrator should confirm that they are happening and that restore procedures are understood.

Ask IT or your technical support team to confirm:
- What is backed up.
- How often backups run.
- Where backups are stored.
- Who can restore the system.
- How long a restore usually takes.
- When the last restore test was completed.

At least periodically, ask for evidence that a backup can be restored. A backup that has never been tested may not be reliable during an emergency.

## Security and Privacy

Super Administrators are responsible for strong access control.

- Use named accounts. Do not share accounts.
- Keep Super Administrator access limited.
- Deactivate leavers promptly.
- Review administrator access regularly.
- Require temporary passwords to be changed at first login.
- Do not export reports to personal devices or unapproved locations.
- Escalate suspected misuse, missing packages, or unauthorised access.
- Follow your organisation's rules for confidential, legal, medical, financial, or high-value mail.

## Incident Handling

### System Unavailable

1. Confirm whether the issue affects one user or everyone.
2. Ask another user to try from another approved device.
3. Contact IT or technical support.
4. Inform the mailroom team of the temporary process to use while the system is unavailable.
5. When the system is restored, enter any packages that were handled manually.

### Missing or Disputed Package

1. Search by tracking number, recipient, department, and date.
2. Open the package record and review status history, notes, and photos.
3. Check whether a QR scan or status update was recorded.
4. Speak with the operator or recipient if needed.
5. Follow the organisation's incident process for unresolved or sensitive items.

### Suspected Account Misuse

1. Deactivate or reset the affected account if appropriate.
2. Review audit logs for recent activity.
3. Notify IT, Security, or management according to policy.
4. Document the action taken.

### QR Codes Open the Wrong Address

1. Stop printing new QR stickers.
2. Open **System Settings** and check the QR code base URL.
3. Ask IT to confirm the correct address.
4. Update the setting.
5. Print and scan a test sticker.
6. Reprint affected stickers if needed.

## Working with IT or Technical Support

Contact IT or technical support for:
- System outage.
- Browser certificate or security warning.
- Network or VPN issue.
- Backup or restore work.
- Server, database, storage, or log investigation.
- Failed uploads affecting many users.
- QR codes that cannot be reached from approved devices.

When raising a support request, provide:
- What happened.
- When it started.
- Who is affected.
- Screenshots if allowed.
- Package ID or tracking number if relevant.
- Any recent setting or user changes.

## Handover Checklist

Use this when another person takes over Super Administrator duties.

- Confirm all current Super Administrators.
- Review Administrator accounts.
- Explain the recipient import process and data source.
- Review QR code settings.
- Review the audit log location and common filters.
- Confirm backup and restore contacts.
- Confirm support escalation contacts.
- Review recent incidents or unresolved mailroom issues.

## Quick Reference

### Super Administrator Can Do

- Manage all user roles.
- Review audit logs.
- Maintain system settings available in the application.
- Oversee recipient data quality.
- Coordinate backups, recovery, and incidents with IT.
- Set mailroom operating rules for system use.

### Use IT or Technical Support For

- Server setup or restart.
- Database access.
- Backup restore.
- Network, VPN, or certificate problems.
- Storage, log, or performance investigation.
- Application upgrades.

### Who to Contact

- **Daily mailroom process**: Mailroom manager or operations lead.
- **Technical outage**: IT support.
- **Security concern**: Security team, IT, or management.
- **Recipient source data**: HR, Facilities, or department coordinator.

---

**Version**: 2.1
**Last Updated**: November 2025
**Maintained By**: System Owner / Super Administrator
