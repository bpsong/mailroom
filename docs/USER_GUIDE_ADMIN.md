# Administrator User Guide

## Who This Guide Is For

This guide is for mailroom supervisors, team leads, or authorised staff who manage daily mailroom records in the Mailroom Tracking System. It is written for non-technical users who support the mailroom team and keep package, recipient, and user information accurate.

As an **Administrator**, you can do everything an Operator can do, plus:
- Create and manage Operator accounts and, if allowed by your organisation, other Administrator accounts.
- Keep the recipient list accurate.
- Add or update recipients in bulk with a CSV file.
- View reports for package volume, delivery status, and mailroom workload.
- Help operators with common access and data issues.

Super Administrators have additional system ownership responsibilities, such as system settings and audit review.

## Basic Terms

- **Operator**: A mailroom staff member who registers, searches, and updates packages.
- **Recipient**: The staff member or department receiving the item.
- **User account**: A login account for someone who uses the system.
- **CSV file**: A spreadsheet-style file used to import many recipient records at once.
- **Report**: A filtered list or export of package activity.

## Logging In

1. Open the Mailroom Tracking System in your web browser.
2. Enter your administrator username and password.
3. Click **Login**.

Administrators usually see extra menu items such as:
- **Recipients**.
- **Users**.
- **Reports**.

Log out when you finish, especially on a shared workstation.

## Managing Users

Use **Users** to manage access for mailroom staff.

### View Users

1. Click **Users**.
2. Review the user list.

The list usually shows:
- Username.
- Full name.
- Role.
- Status.
- Created date.

### Create a New User

1. Click **Users**.
2. Click **Add New User**.
3. Enter the user's details:
   - **Username**: The name they use to log in.
   - **Full Name**: Their display name.
   - **Role**: Choose **Operator** for daily mailroom staff, or **Administrator** for authorised supervisors.
   - **Initial Password**: A temporary password.
4. Click **Create User**.
5. Give the login details to the user using your organisation's approved secure method.
6. Ask the user to log in and change the temporary password.

Only give Administrator access to staff who genuinely need it.

### Edit a User

1. Click **Users**.
2. Find the user.
3. Click **Edit**.
4. Update the allowed details, such as full name or role.
5. Click **Save Changes**.

You may not be able to edit Super Administrator accounts or your own role.

### Reset a Password

Use this when a user forgets their password or cannot access the system.

1. Click **Users**.
2. Find the user.
3. Click **Reset Password**.
4. Enter a new temporary password.
5. Keep the option enabled that requires the user to change the password at next login.
6. Click **Reset Password**.
7. Give the temporary password to the user using a secure method.

Do not send passwords in open group chats or leave them written at shared desks.

### Deactivate a User

Deactivate a user when they leave the mailroom, change role, or no longer need access.

1. Click **Users**.
2. Find the user.
3. Click **Deactivate**.
4. Confirm the action.

After deactivation:
- The user cannot log in.
- Their past package activity remains in the system.
- Their name may still appear in package history and reports.

You cannot deactivate your own account. If you need help with your own access, contact a Super Administrator.

### Search for Users

Use the search bar to find users by:
- Username.
- Full name.
- Role.
- Status.

## Managing Recipients

Recipients are the people or departments that receive packages. Keeping this list accurate helps operators select the correct recipient and deliver items faster.

### View Recipients

1. Click **Recipients**.
2. Review the recipient list.

The list usually shows:
- Employee ID.
- Name.
- Email.
- Department.
- Phone.
- Location.
- Status.

### Add a New Recipient

1. Click **Recipients**.
2. Click **Add New Recipient**.
3. Enter the recipient details:
   - **Employee ID**: The organisation's employee or staff identifier.
   - **Name**: Full name.
   - **Email**: Work email address.
   - **Department**: Recipient's department.
   - **Phone**: Phone or extension, if used.
   - **Location**: Building, floor, office, desk area, or mail stop.
4. Click **Create Recipient**.

Check spelling, department, and location before saving. Operators rely on these details during sorting and delivery.

### Edit a Recipient

1. Click **Recipients**.
2. Find the recipient.
3. Click **Edit**.
4. Update the details.
5. Click **Save Changes**.

Update recipient records when someone changes department, building, floor, name, email, or phone extension.

### Deactivate a Recipient

Deactivate a recipient when the person has left the organisation or should no longer receive packages through the mailroom.

1. Click **Recipients**.
2. Find the recipient.
3. Click **Deactivate**.
4. Confirm the action.

After deactivation:
- The recipient will not appear in normal selection lists for new packages.
- Existing package history remains unchanged.
- Old reports and records still show the original recipient.

If a recipient record was created by mistake, follow your organisation's data correction process.

### Search for Recipients

Use the search bar to find recipients by:
- Employee ID.
- Name.
- Email.
- Department.
- Location.

## Importing Recipients from a CSV File

Use CSV import when you need to add or update many recipients, such as after receiving an updated staff list from HR or Facilities.

### Before You Import

Prepare the file carefully. A clean file saves time and avoids wrong deliveries.

The CSV file should include these columns:

| Column | Required | What It Means |
|--------|----------|---------------|
| employee_id | Yes | Staff or employee identifier. |
| name | Yes | Recipient's full name. |
| email | Yes | Work email address. |
| department | Yes | Department or business unit. |
| phone | No | Phone number or extension. |
| location | No | Building, floor, office, desk area, or mail stop. |

Example:

```csv
employee_id,name,email,department,phone,location
E12345,John Smith,john.smith@company.com,Facilities,555-0100,Building A Floor 2
E12346,Jane Doe,jane.doe@company.com,Finance,555-0101,Building B Floor 5
E12347,Bob Johnson,bob.johnson@company.com,Sales,555-0102,Building A Floor 4
```

### Import the File

1. Click **Recipients**.
2. Click **Import CSV**.
3. Choose or drag in the CSV file.
4. Click **Upload and Validate**.
5. Review the results before confirming.

### Review the Validation Results

The system checks the file before importing. It may show:
- **Valid records**: Rows that can be imported.
- **New records**: Recipients that will be added.
- **Updates**: Existing recipients that will be updated.
- **Errors**: Rows that must be fixed before import.

Common errors include:
- Missing employee ID, name, email, or department.
- Duplicate employee IDs in the file.
- Email addresses in the wrong format.
- Very long values that do not fit the field.

### Confirm the Import

1. Read the validation summary.
2. If errors appear, cancel the import, fix the file, and upload again.
3. If the file is correct, click **Confirm Import**.
4. Wait for the success message.
5. Spot-check a few recipient records after import.

### CSV Import Good Practice

- Start with a small test file if this is your first import.
- Keep department and location names consistent.
- Remove duplicate rows before uploading.
- Keep a copy of the file you imported.
- Import updated recipient lists on a regular schedule agreed with HR, Facilities, or your supervisor.

## Reports

Reports help supervisors understand workload, follow up on delayed items, and answer questions from departments.

### Dashboard Metrics

The dashboard may show:
- Packages registered today.
- Packages awaiting pickup.
- Packages delivered today.
- Package status breakdown.
- Top recipients or departments.

Use these numbers as a quick health check for the day.

### View a Report

1. Click **Reports**.
2. Choose filters such as:
   - Date range.
   - Status.
   - Department.
   - Operator.
   - Carrier.
3. Click **Apply Filters**.
4. Review the results.

### Export a Report

1. Open **Reports**.
2. Apply the filters you need.
3. Click **Export to CSV**.
4. Open the downloaded file in Excel or your approved spreadsheet tool.

Exports may contain recipient names, email addresses, departments, and package details. Store and share exported files according to your organisation's data handling rules.

### Useful Report Checks

**Daily open items**
1. Filter for **Awaiting Pickup** and **Out for Delivery**.
2. Check items that have been waiting too long.
3. Ask operators to follow up or update statuses.

**Department volume**
1. Filter by department.
2. Choose a date range.
3. Export if the department needs a copy.

**Operator activity**
1. Filter by operator.
2. Choose a date range.
3. Review package registration and status updates.

**Old awaiting pickup items**
1. Filter by **Awaiting Pickup**.
2. Sort by oldest first.
3. Follow up with recipients or departments.

## Daily Administrator Checks

Use this short checklist to keep the mailroom data clean.

- Check the dashboard for unusual package volumes.
- Review packages still awaiting pickup from previous days.
- Confirm new employees or moved employees are reflected in the recipient list.
- Help operators with locked accounts or password resets.
- Deactivate accounts and recipients that are no longer valid.

## Monthly Administrator Checks

- Review the user list and remove access that is no longer needed.
- Import or update the latest recipient list.
- Export the monthly package report if required.
- Review departments or locations with frequent delivery issues.
- Check for repeated recipient search problems and correct the underlying data.

## Security and Privacy

Mailroom records may contain personal and business information. Treat them carefully.

- Do not share your administrator account.
- Give users only the access they need.
- Deactivate access promptly when someone leaves or changes role.
- Do not leave package records visible on shared screens.
- Store exported reports only in approved locations.
- Report suspicious access, missing packages, or unusual changes to a Super Administrator or IT.

## Troubleshooting

### Cannot Find a Recipient

- Search by name, employee ID, email, and department.
- Check for spelling variations.
- Add or update the recipient record if you are sure the details are correct.
- Ask HR, Facilities, or the recipient's department to confirm uncertain details.

### Employee ID Already Exists

- Search for the existing recipient.
- Update the existing record instead of creating a duplicate.
- If there are two people with similar details, confirm with HR or your supervisor before changing records.

### CSV Import Failed

- Read the validation message.
- Check that required columns are present.
- Remove duplicate employee IDs.
- Save the file as CSV, not Excel format.
- Try a smaller file if needed.

### User Cannot Log In

- Check whether the account is active.
- Reset the password if needed.
- Ask the user to try again after any lockout period.
- Escalate to a Super Administrator if several users cannot log in.

### Export Not Working

- Check the browser download area.
- Try the export again with fewer filters or a shorter date range.
- Ask IT or a Super Administrator if downloads are blocked.

## Quick Reference

### Administrator Can Do

- Register and update packages.
- Create and manage Operator accounts and authorised Administrator accounts.
- Manage recipients.
- Import recipient CSV files.
- View and export reports.
- Help operators with everyday access and data issues.

### Administrator Cannot Usually Do

- Change system-wide settings.
- Manage Super Administrator accounts.
- Directly access the server or database.
- Change audit records.

### Who to Contact

- **System setting or audit question**: Super Administrator.
- **Technical outage**: IT support or Super Administrator.
- **Recipient list source issue**: HR, Facilities, or department contact.
- **Mailroom process decision**: Mailroom supervisor or operations manager.

---

**Version**: 1.1
**Last Updated**: November 2025
**For Support**: Contact your Super Administrator
