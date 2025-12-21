# Operator User Guide

## Introduction

Welcome to the Mailroom Tracking System! This guide will help you learn how to register packages, update their status, and search for packages in the system.

As an **Operator**, you are responsible for:
- Registering incoming packages
- Updating package status as they move through the delivery workflow
- Searching for packages to check their status
- Viewing package details and history

## Getting Started

### Logging In

1. Open your web browser and navigate to the Mailroom Tracking System URL
2. Enter your **username** and **password**
3. Click the **Login** button

**Important Security Notes:**
- Your session will automatically expire after 30 minutes of inactivity
- After 5 failed login attempts, your account will be locked for 30 minutes
- If you forget your password, contact your administrator

### Changing Your Password

You can change your password at any time:

1. Click on your profile icon in the top-right corner
2. Select **Change Password** from the dropdown menu
3. Enter your current password
4. Enter your new password (must be at least 12 characters with uppercase, lowercase, numbers, and symbols)
5. Confirm your new password
6. Click **Update Password**

### Logging Out

Always log out when you're finished:

1. Click on your profile icon in the top-right corner
2. Select **Logout** from the dropdown menu

## Dashboard Overview

When you log in, you'll see the dashboard with:

- **Packages Today**: Total packages registered today
- **Awaiting Pickup**: Packages ready for recipient pickup
- **Delivered Today**: Packages delivered today
- **Quick Search**: Search bar to find packages quickly

Click on any metric card to filter the package list by that status.

## Registering a New Package

### Step-by-Step Process

1. Click **Register Package** in the sidebar or navigation menu
2. Fill in the package information:
   - **Tracking Number**: Enter the carrier's tracking number (required)
   - **Carrier**: Select the shipping carrier (UPS, FedEx, USPS, DHL, Other)
   - **Recipient**: Start typing the recipient's name and select from the autocomplete list (required)
   - **Notes**: Add any additional information (optional, max 500 characters)
3. **Add Photo** (optional but recommended):
   - Click the **Choose File** button or drag and drop an image
   - On mobile devices, you can use the camera to take a photo directly
   - Supported formats: JPEG, PNG, WebP (max 5MB)
4. Click **Register Package**
5. You'll see a success message and the package will appear in the package list

### Tips for Package Registration

- **Use the camera on mobile**: When registering packages on a tablet or phone, tap the camera icon to take a photo directly
- **Recipient autocomplete**: Start typing just a few letters of the recipient's name, and the system will show matching results
- **Multiple photos**: You can add additional photos after registration by viewing the package details
- **Tracking numbers**: The same tracking number can be used for multiple packages if needed

## Updating Package Status

Packages move through different statuses in their lifecycle:

1. **Registered** - Package has been logged into the system
2. **Awaiting Pickup** - Package is ready for the recipient to collect
3. **Out for Delivery** - Package is being delivered to the recipient
4. **Delivered** - Package has been successfully delivered
5. **Returned** - Package was returned to sender

### How to Update Status

**Method 1: From Package List**
1. Go to **Packages** in the sidebar
2. Find the package you want to update
3. Click the **Status** dropdown next to the package
4. Select the new status
5. Add notes if needed (optional)
6. Click **Update**

**Method 2: From Package Details**
1. Click on a package to view its details
2. Click the **Update Status** button
3. Select the new status from the dropdown
4. Add notes to explain the status change (optional)
5. Click **Confirm**

### Status Change Guidelines

- **Registered → Awaiting Pickup**: When you've sorted the package and it's ready for pickup
- **Awaiting Pickup → Delivered**: When the recipient picks up the package directly
- **Awaiting Pickup → Out for Delivery**: When you're delivering the package to the recipient's location
- **Out for Delivery → Delivered**: When you've successfully delivered the package
- **Out for Delivery → Returned**: When delivery failed and the package is being returned

### Adding Notes

When updating status, you can add notes to provide context:
- "Recipient notified via email"
- "Left at front desk"
- "Signature required - recipient unavailable"
- "Damaged package - recipient refused"

Notes help maintain a clear audit trail and are visible in the package timeline.

## Searching for Packages

### Quick Search

Use the search bar on the dashboard or package list page:

1. Type any of the following:
   - Tracking number
   - Recipient name
   - Department name
2. Results appear as you type
3. Click on a package to view details

### Advanced Filtering

On the **Packages** page, you can filter by:

- **Status**: Select one or more statuses to filter
- **Date Range**: Choose start and end dates
- **Department**: Filter by recipient department
- **Carrier**: Filter by shipping carrier

Click **Apply Filters** to update the results.

### Viewing Package Details

Click on any package to see:

- Full package information (tracking number, carrier, recipient)
- Current status
- All photos attached to the package
- Complete status history timeline showing:
  - What status changed
  - When it changed
  - Who made the change
  - Any notes added

#### QR Code Actions

Each package detail page includes a **QR Code** card so you can generate or reprint stickers without leaving the page:

1. Scroll to the QR panel on the detail page.
2. Select **Download PNG** to save `qr_code_{package_id}.png` for use in other design tools or to email the code.
3. Select **Print Sticker** to open the minimalist 2 cm × 2 cm print view in a new tab, then press your browser's print button to send it to a label printer.
4. Place the sticker on the package before it leaves the mailroom so future scans pull up the correct record.

When another operator scans a sticker, they'll be asked to log in (if they are not already authenticated). After login, the system automatically forwards them back to that package's detail page so they can update the status from their phone.

## Mobile Usage

The Mailroom Tracking System is optimized for mobile devices:

### Navigation on Mobile

- Tap the **☰ menu icon** in the top-left to open the navigation sidebar
- Tap outside the sidebar or the X to close it

### Registering Packages on Mobile

1. The form is optimized for touch input
2. Use the **camera button** to take photos directly
3. All buttons are sized for easy tapping
4. The keyboard will automatically show the correct type (text, number, etc.)
5. QR options are mobile-friendly: tap **QR Actions** on the package card, then choose **Download** (saves to your device) or **Print** (opens the print view for AirPrint / default printer).

### Best Practices for Mobile

- Use landscape mode for viewing package lists
- Use portrait mode for registering packages
- Take photos in good lighting for better quality
- The system works offline within your corporate network

## Common Tasks

### Finding a Package for a Recipient

1. Go to **Packages** in the sidebar
2. Use the search bar and type the recipient's name
3. Or use filters to narrow down by department
4. Click on the package to see details

### Checking What Needs Pickup

1. From the dashboard, click the **Awaiting Pickup** card
2. You'll see all packages ready for pickup
3. Sort by recipient or department to organize your work

### Viewing Your Activity

All your actions are logged in the system:
- Package registrations show your name as "Created by"
- Status updates show your name in the timeline
- Your administrator can view detailed audit logs

## Troubleshooting

### "Recipient not found"

If you can't find a recipient in the autocomplete:
- Check the spelling
- Try searching by employee ID or email
- Contact your administrator to add the recipient

### "Session expired"

If you see this message:
- Your session timed out after 30 minutes of inactivity
- Simply log in again to continue

### "File too large"

If you can't upload a photo:
- The maximum file size is 5MB
- Try taking a new photo with lower resolution
- Or compress the image before uploading

### "Account locked"

If you can't log in:
- You may have exceeded 5 failed login attempts
- Wait 30 minutes and try again
- Or contact your administrator to unlock your account

### Page not loading or errors

- Refresh the page (F5 or Ctrl+R)
- Clear your browser cache
- Try a different browser (Chrome, Firefox, Edge)
- Contact your administrator if the problem persists

## Tips for Efficient Operation

1. **Register packages as they arrive**: Don't let them pile up
2. **Take photos immediately**: It's easier than going back later
3. **Use meaningful notes**: Help your team understand what happened
4. **Update status promptly**: Keep recipients informed
5. **Use mobile devices**: Register packages right at the mailroom counter
6. **Check "Awaiting Pickup" daily**: Follow up on packages waiting too long

## Getting Help

If you need assistance:

- **Technical issues**: Contact your IT administrator
- **System access**: Contact your mailroom administrator
- **Training**: Ask your supervisor for additional training
- **Feature requests**: Provide feedback to your administrator

## Quick Reference

### Keyboard Shortcuts

- **Tab**: Move between form fields
- **Enter**: Submit forms
- **Esc**: Close modals and dialogs
- **Ctrl+F**: Focus search bar (on some browsers)

### Status Colors

- **Gray**: Registered
- **Yellow**: Awaiting Pickup
- **Blue**: Out for Delivery
- **Green**: Delivered
- **Red**: Returned

### Required Fields

Fields marked with an asterisk (*) are required:
- Tracking Number *
- Carrier *
- Recipient *

---

**Version**: 1.0  
**Last Updated**: November 2025  
**For Support**: Contact your system administrator
