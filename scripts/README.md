# Deployment Scripts

This directory contains PowerShell scripts for deploying and maintaining the Mailroom Tracking System on Windows Server.

## Scripts Overview

### install_service.ps1
Installs the application as a Windows Service using NSSM (Non-Sucking Service Manager).

**Usage:**
```powershell
.\install_service.ps1 [options]
```

**Key Features:**
- Creates Windows Service with automatic startup
- Configures service restart on failure
- Sets up logging (stdout/stderr)
- Validates prerequisites (NSSM, Python, application files)

**Common Commands:**
```powershell
# Install with defaults
.\install_service.ps1

# Install with custom path
.\install_service.ps1 -InstallPath "D:\Apps\Mailroom"

# Uninstall service
.\install_service.ps1 -Uninstall

# Show help
.\install_service.ps1 -Help
```

---

### init_database.ps1
Initializes the database schema and creates the super admin account.

**Usage:**
```powershell
.\init_database.ps1 [options]
```

**Key Features:**
- Creates database schema with all tables
- Creates super admin account with secure password
- Validates password strength (min 12 characters)
- Supports database reset (WARNING: deletes all data)

**Common Commands:**
```powershell
# Initialize with defaults (prompts for password)
.\init_database.ps1

# Initialize with custom super admin
.\init_database.ps1 -SuperAdminUsername "superadmin" -SuperAdminFullName "John Doe"

# Reset database (deletes all data)
.\init_database.ps1 -ResetDatabase

# Show help
.\init_database.ps1 -Help
```

**IMPORTANT:** Save the super admin credentials securely after initialization!

---

### backup.ps1
Creates backups of the database, uploaded files, and configuration.

**Usage:**
```powershell
.\backup.ps1 [options]
```

**Key Features:**
- Backs up DuckDB database (including WAL files)
- Backs up uploaded package photos
- Backs up .env configuration
- Creates backup manifest with details
- Compresses backup to ZIP (optional)
- Shows disk space information

**Common Commands:**
```powershell
# Create backup with defaults
.\backup.ps1

# Create backup to custom location
.\backup.ps1 -BackupPath "D:\Backups\Mailroom"

# Create uncompressed backup (faster)
.\backup.ps1 -SkipCompression

# Show help
.\backup.ps1 -Help
```

**Backup Location:** `C:\Backups\Mailroom\mailroom_backup_YYYYMMDD_HHMMSS.zip`

---

### cleanup_backups.ps1
Removes old backups based on retention policy (default: 30 days).

**Usage:**
```powershell
.\cleanup_backups.ps1 [options]
```

**Key Features:**
- Finds backups older than retention period
- Shows backup details (age, size)
- Dry run mode for preview
- Confirmation prompt (unless -Force)
- Summary of deleted backups and freed space

**Common Commands:**
```powershell
# Preview cleanup (dry run)
.\cleanup_backups.ps1 -DryRun

# Clean backups older than 30 days (default)
.\cleanup_backups.ps1

# Clean backups older than 90 days
.\cleanup_backups.ps1 -RetentionDays 90

# Clean without confirmation
.\cleanup_backups.ps1 -Force

# Show help
.\cleanup_backups.ps1 -Help
```

---

## Deployment Workflow

### Initial Deployment

1. **Deploy application files** to `C:\MailroomApp`
2. **Install Python dependencies:** `pip install -e .`
3. **Create .env file:** `Copy-Item .env.example .env`
4. **Configure .env** with production settings
5. **Initialize database:** `.\scripts\init_database.ps1`
6. **Install service:** `.\scripts\install_service.ps1`
7. **Start service:** `Start-Service MailroomTracking`

### Scheduled Maintenance

Set up automated tasks for backups and cleanup:

**Daily Backup (2 AM):**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\MailroomApp\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
Register-ScheduledTask -TaskName "MailroomBackup" -Action $action -Trigger $trigger -Principal $principal
```

**Weekly Cleanup (Sunday 3 AM):**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\MailroomApp\scripts\cleanup_backups.ps1 -Force"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
Register-ScheduledTask -TaskName "MailroomBackupCleanup" -Action $action -Trigger $trigger -Principal $principal
```

## Prerequisites

### Required Software

- **Python 3.12+**: https://www.python.org/downloads/
- **NSSM**: https://nssm.cc/download or `choco install nssm`
- **PowerShell 5.1+**: Included with Windows

### Required Permissions

- Administrator access (for service installation)
- Write permissions to installation directory
- Write permissions to backup directory

## Troubleshooting

### Script Execution Policy

If scripts won't run due to execution policy:

```powershell
# Check current policy
Get-ExecutionPolicy

# Allow scripts (run as Administrator)
Set-ExecutionPolicy RemoteSigned -Scope LocalMachine

# Or run with bypass
powershell -ExecutionPolicy Bypass -File .\script.ps1
```

### Common Issues

**"NSSM is not installed"**
- Install NSSM: `choco install nssm`
- Or download from: https://nssm.cc/download

**"Python not found"**
- Verify Python installation: `python --version`
- Specify Python path: `-PythonPath "C:\Python312\python.exe"`

**"Database already exists"**
- Use `-ResetDatabase` to recreate (WARNING: deletes all data)
- Or continue with existing database

**"Access denied"**
- Run PowerShell as Administrator
- Check file permissions on installation directory

## Additional Resources

- [Deployment Guide](../docs/DEPLOYMENT.md) - Complete deployment instructions
- [Configuration Guide](../docs/CONFIGURATION.md) - Environment configuration
- [NSSM Documentation](https://nssm.cc/usage) - Service manager details

## Support

For issues or questions:
1. Check the [Deployment Guide](../docs/DEPLOYMENT.md)
2. Review script help: `.\script.ps1 -Help`
3. Check application logs: `C:\MailroomApp\logs\`
