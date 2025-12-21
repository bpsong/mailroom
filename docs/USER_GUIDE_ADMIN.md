# Administrator User Guide

## Introduction

Welcome to the Mailroom Tracking System Administrator Guide. This guide covers all administrative functions including user management, recipient management, CSV imports, and reporting.

As an **Administrator**, you have all operator capabilities plus:
- Managing user accounts (creating, editing, deactivating operators)
- Managing the recipient database
- Importing recipients via CSV
- Generating and exporting reports
- Viewing system statistics and analytics

**Note**: Super Admins have additional privileges covered in the Super Admin Guide.

## Getting Started

### Logging In

1. Navigate to the Mailroom Tracking System URL
2. Enter your administrator username and password
3. Click **Login**

Your administrator account has access to additional menu items:
- **Recipients** - Manage recipient database
- **Users** - Manage operator accounts
- **Reports** - View analytics and export data

## User Management

### Viewing Users

1. Click **Users** in the sidebar
2. You'll see a list of all users with:
   - Username
   - Full name
   - Role (Operator, Admin, Super Admin)
   - Status (Active/Inactive)
   - Last login date

### Creating a New User

1. Click **Users** in the sidebar
2. Click the **Add New User** button
3. Fill in the user information:
   - **Username**: Unique identifier for login (required)
   - **Full Name**: User's display name (required)
   - **Role**: Select Operator or Admin (required)
   - **Initial Password**: Temporary password (required, min 12 characters)
   - **Force Password Change**: Check to require password change on first login (recommended)
4. Click **Create User**

**Password Requirements**:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

**Best Practices**:
- Always check "Force Password Change" for new users
- Use a secure temporary password
- Communicate the temporary password securely (not via email)
- Verify the username is correct before creating

### Editing a User

1. Click **Users** in the sidebar
2. Find the user you want to edit
3. Click the **Edit** button next to their name
4. Update the information:
   - Full name
   - Role (Operator or Admin)
5. Click **Save Changes**

**Important Restrictions**:
- You cannot edit Super Admin accounts
- You cannot change usernames after creation
- You cannot edit your own role

### Resetting a User's Password

1. Click **Users** in the sidebar
2. Find the user
3. Click the **Reset Password** button
4. Enter a new temporary password
5. Check **Force Password Change** (recommended)
6. Click **Reset Password**

The user will need to change their password on next login if you checked the box.

### Deactivating a User

When an employee leaves or no longer needs access:

1. Click **Users** in the sidebar
2. Find the user
3. Click the **Deactivate** button
4. Confirm the action

**What happens when you deactivate a user**:
- The user cannot log in
- All active sessions are terminated immediately
- The user's historical data remains in the system
- You can reactivate the user later if needed

**Note**: You cannot deactivate Super Admin accounts or your own account.

### Reactivating a User

1. Click **Users** in the sidebar
2. Filter to show inactive users
3. Find the user
4. Click the **Reactivate** button
5. Optionally reset their password

### Searching for Users

Use the search bar to find users by:
- Username
- Full name
- Role

Use filters to show:
- Active users only
- Inactive users only
- Specific roles (Operator, Admin, Super Admin)

## Recipient Management

### Viewing Recipients

1. Click **Recipients** in the sidebar
2. You'll see a list of all recipients with:
   - Employee ID
   - Name
   - Email
   - Department
   - Phone
   - Location
   - Status (Active/Inactive)

### Adding a New Recipient

1. Click **Recipients** in the sidebar
2. Click the **Add New Recipient** button
3. Fill in the recipient information:
   - **Employee ID**: Unique identifier (required)
   - **Name**: Full name (required)
   - **Email**: Email address (required, must be valid format)
   - **Department**: Department name (required)
   - **Phone**: Phone number (optional)
   - **Location**: Office location or building (optional)
4. Click **Create Recipient**

**Validation Rules**:
- Employee ID must be unique
- Email must be in valid format (contains @ and domain)
- All required fields must be filled

### Editing a Recipient

1. Click **Recipients** in the sidebar
2. Find the recipient
3. Click the **Edit** button
4. Update the information
5. Click **Save Changes**

**Note**: You cannot change the Employee ID after creation. If you need to change it, deactivate the old record and create a new one.

### Deactivating a Recipient

When an employee leaves the organization:

1. Click **Recipients** in the sidebar
2. Find the recipient
3. Click the **Deactivate** button
4. Confirm the action

**What happens when you deactivate a recipient**:
- They won't appear in autocomplete searches for new packages
- Existing packages remain linked to them
- Historical data is preserved
- You can reactivate them later if needed

### Searching for Recipients

Use the search bar to find recipients by:
- Employee ID
- Name
- Email
- Department

The search provides autocomplete suggestions as you type.

## CSV Recipient Import

The CSV import feature allows you to bulk-add or update recipients from a spreadsheet.

### Preparing Your CSV File

Your CSV file must have these columns (in any order):

- **employee_id** - Unique employee identifier (required)
- **name** - Full name (required)
- **email** - Email address (required)
- **department** - Department name (required)
- **phone** - Phone number (optional)
- **location** - Office location (optional)

**Example CSV**:
```csv
employee_id,name,email,department,phone,location
E12345,John Smith,john.smith@company.com,Engineering,555-0100,Building A
E12346,Jane Doe,jane.doe@company.com,Marketing,555-0101,Building B
E12347,Bob Johnson,bob.johnson@company.com,Sales,555-0102,Building A
```

**CSV File Requirements**:
- First row must be headers
- Maximum 1000 rows per file
- UTF-8 encoding recommended
- Comma-separated values

### Importing Recipients

1. Click **Recipients** in the sidebar
2. Click the **Import CSV** button
3. Click **Choose File** or drag and drop your CSV file
4. Click **Upload and Validate**

### Validation Process

The system will perform a dry-run validation and show you:

- **Valid Records**: Rows that will be imported successfully
- **Errors**: Rows with problems that must be fixed
- **Updates**: Existing recipients that will be updated (matched by employee_id)
- **New Records**: New recipients that will be created

**Common Validation Errors**:
- Missing required fields (employee_id, name, email, department)
- Invalid email format
- Duplicate employee_ids within the file
- Row exceeds maximum field lengths

### Reviewing and Confirming Import

1. Review the validation report carefully
2. If there are errors:
   - Click **Cancel**
   - Fix the errors in your CSV file
   - Upload again
3. If validation passes:
   - Review the summary (X new, Y updates)
   - Click **Confirm Import**
4. Wait for the import to complete
5. You'll see a success message with the final count

### Import Behavior

- **New employee_id**: Creates a new recipient record
- **Existing employee_id**: Updates the existing recipient with new data
- **All changes are logged**: The audit log records who imported, when, and how many records

### Best Practices for CSV Import

1. **Test with a small file first**: Import 5-10 records to verify format
2. **Back up your data**: Export current recipients before large imports
3. **Validate in Excel first**: Check for duplicates and missing data
4. **Use consistent formatting**: Keep department names consistent
5. **Import during off-hours**: Large imports may take a few minutes

### Troubleshooting CSV Import

**"Invalid CSV format"**
- Ensure the first row contains headers
- Check that columns are comma-separated
- Verify the file is saved as .csv (not .xlsx)

**"File too large"**
- Maximum 1000 rows per file
- Split large files into multiple smaller files

**"Duplicate employee_id"**
- Check your CSV for duplicate employee IDs
- Remove duplicates before importing

**"Invalid email format"**
- Ensure all emails contain @ and a domain
- Fix any typos in email addresses

## Reports and Analytics

### Dashboard Overview

The dashboard shows key metrics:

- **Packages Today**: Total packages registered today
- **Awaiting Pickup**: Packages currently waiting for pickup
- **Delivered Today**: Packages delivered today
- **Top Recipients**: Top 5 recipients by package count this month
- **Status Distribution**: Breakdown of packages by status

Click on any metric to filter the package list.

### Viewing Reports

1. Click **Reports** in the sidebar
2. Select your filters:
   - **Date Range**: Start and end dates
   - **Status**: Filter by package status
   - **Department**: Filter by recipient department
   - **Operator**: Filter by who registered the package
3. Click **Apply Filters**
4. View the results in the table

### Exporting Data

To export package data to CSV:

1. Go to **Reports**
2. Apply your desired filters
3. Click the **Export to CSV** button
4. The file will download to your computer

**CSV Export Includes**:
- Tracking number
- Carrier
- Recipient name
- Recipient email
- Department
- Status
- Created date/time
- Updated date/time
- Created by (operator name)
- Notes

### Common Report Scenarios

**Monthly Package Volume**:
1. Set date range to first and last day of the month
2. Export to CSV
3. Use Excel to create pivot tables and charts

**Packages by Department**:
1. Filter by department
2. Set date range as needed
3. View or export results

**Operator Performance**:
1. Filter by operator
2. Set date range (e.g., last week)
3. View how many packages they registered

**Overdue Pickups**:
1. Filter status to "Awaiting Pickup"
2. Sort by created date (oldest first)
3. Follow up on packages waiting more than 3 days

## System Monitoring

### Checking System Health

As an administrator, monitor these indicators:

**Active Users**:
- Check the user list regularly
- Deactivate accounts for employees who have left
- Review last login dates to identify inactive accounts

**Package Volume**:
- Monitor daily package counts
- Look for unusual spikes or drops
- Ensure operators are registering packages promptly

**Recipient Database**:
- Keep recipient information up to date
- Deactivate former employees
- Import new employees regularly

### Performance Tips

**Keep the recipient list clean**:
- Deactivate former employees
- Update department changes
- Fix incorrect email addresses

**Regular CSV imports**:
- Import new employees weekly or monthly
- Keep data synchronized with HR systems

**Monitor storage**:
- Package photos consume disk space
- Contact your Super Admin if storage is running low

## Security Best Practices

### Password Management

- Enforce strong passwords for all users
- Always use "Force Password Change" for new accounts
- Reset passwords immediately if an account is compromised
- Never share your administrator password

### User Account Hygiene

- Deactivate accounts promptly when employees leave
- Review user list monthly for inactive accounts
- Use the principle of least privilege (only make users admins if needed)
- Monitor the audit log for suspicious activity

### Data Protection

- Don't export sensitive data to unsecured locations
- Be careful with CSV exports containing personal information
- Follow your organization's data retention policies
- Report any security concerns to your Super Admin

## Common Administrative Tasks

### Onboarding a New Operator

1. Create their user account with role "Operator"
2. Set a temporary password and check "Force Password Change"
3. Provide them with the Operator User Guide
4. Have them log in and change their password
5. Verify they can access the system

### Offboarding an Employee

1. Deactivate their user account (if they were an operator)
2. Deactivate their recipient record
3. Their historical data remains in the system

### Monthly Maintenance

1. Review user accounts and deactivate inactive users
2. Import new employees from HR
3. Export monthly package report for records
4. Check for packages stuck in "Awaiting Pickup" status
5. Review dashboard metrics for trends

### Quarterly Review

1. Export all package data for the quarter
2. Analyze trends by department
3. Identify top recipients
4. Review operator activity
5. Clean up inactive recipients

## Troubleshooting

### "Cannot edit this user"

- You cannot edit Super Admin accounts
- You cannot edit your own role
- You may not have permission (contact Super Admin)

### "Cannot deactivate this user"

- You cannot deactivate Super Admin accounts
- You cannot deactivate yourself
- The user may already be inactive

### "Employee ID already exists"

- Each employee ID must be unique
- Check if the recipient already exists
- Edit the existing recipient instead of creating a new one

### "CSV import failed"

- Check the validation report for specific errors
- Ensure all required columns are present
- Verify data format (especially emails)
- Try a smaller file if it's very large

### "Export not working"

- Check your browser's download settings
- Ensure pop-ups are not blocked
- Try a different browser
- Contact your Super Admin if the issue persists

## Getting Help

For assistance:

- **User account issues**: Contact your Super Admin
- **Technical problems**: Contact IT support
- **Feature requests**: Discuss with your Super Admin
- **Training**: Refer to this guide or request additional training

## Quick Reference

### Administrator Permissions

✅ Can Do:
- Create, edit, deactivate Operator accounts
- Manage all recipients
- Import recipients via CSV
- View and export all reports
- Register and track packages (operator functions)

❌ Cannot Do:
- Edit or deactivate Super Admin accounts
- View detailed audit logs (Super Admin only)
- Change system configuration
- Access server or database directly

### Keyboard Shortcuts

- **Ctrl+F**: Search on current page
- **Tab**: Navigate between form fields
- **Enter**: Submit forms
- **Esc**: Close modals

### Status Workflow

```
Registered → Awaiting Pickup → Out for Delivery → Delivered
                ↓                      ↓
              Delivered              Returned
```

---

**Version**: 1.0  
**Last Updated**: November 2025  
**For Support**: Contact your Super Administrator
