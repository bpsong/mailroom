# Deployment Guide

This document provides comprehensive instructions for deploying the Mailroom Tracking System on Windows Server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Deployment Scripts](#deployment-scripts)
- [Service Management](#service-management)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Windows Server 2016 or later (or Windows 10/11 Pro)
- **Python**: Python 3.12 or later
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Disk Space**: Minimum 10GB free space
- **Network**: Internal network access (behind corporate firewall)

### Required Software

1. **Python 3.12+**
   - Download from: https://www.python.org/downloads/
   - Ensure "Add Python to PATH" is checked during installation
   - Verify installation: `python --version`

2. **NSSM (Non-Sucking Service Manager)**
   - Option 1 - Chocolatey: `choco install nssm`
   - Option 2 - Manual: Download from https://nssm.cc/download
   - Verify installation: `nssm --version`

3. **Caddy (Recommended - for HTTPS)**
   - Download from: https://caddyserver.com/download
   - Or use Chocolatey: `choco install caddy`
   - See [Caddy Setup Guide](CADDY_SETUP.md) for detailed instructions

### Permissions

- Administrator access to install Windows Service
- Write permissions to installation directory
- Network access to required ports (default: 8000)

## Installation Steps

### Step 1: Deploy Application Files

1. **Create installation directory:**
   ```powershell
   New-Item -ItemType Directory -Path "C:\MailroomApp" -Force
   ```

2. **Copy application files:**
   ```powershell
   # Copy all application files to C:\MailroomApp
   # Ensure the following structure:
   # C:\MailroomApp\
   #   ├── app\
   #   ├── scripts\
   #   ├── static\
   #   ├── templates\
   #   ├── .env.example
   #   └── pyproject.toml
   ```

3. **Install Python dependencies:**
   ```powershell
   cd C:\MailroomApp
   python -m pip install --upgrade pip
   pip install -e .
   ```

### Step 2: Configure Environment

1. **Create .env file:**
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

2. **Set required configuration:**
   ```env
   APP_ENV=production
   SECRET_KEY=<generate-secure-key>
   DATABASE_PATH=C:\MailroomApp\data\mailroom.duckdb
   UPLOAD_DIR=C:\MailroomApp\uploads
   LOG_FILE=C:\MailroomApp\logs\mailroom.log
   ```

3. **Generate secure secret key:**
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

### Step 3: Initialize Database

Run the database initialization script:

```powershell
cd C:\MailroomApp\scripts
.\init_database.ps1
```

**Options:**
- `-InstallPath`: Installation directory (default: C:\MailroomApp)
- `-PythonPath`: Path to Python executable (default: C:\Python312\python.exe)
- `-SuperAdminUsername`: Super admin username (default: admin)
- `-SuperAdminFullName`: Super admin full name
- `-ResetDatabase`: Delete existing database and recreate (WARNING: deletes all data)

**Example:**
```powershell
# Initialize with custom super admin
.\init_database.ps1 -SuperAdminUsername "superadmin" -SuperAdminFullName "John Doe"

# Reset database (deletes all data)
.\init_database.ps1 -ResetDatabase
```

The script will:
- Validate Python installation
- Check .env configuration
- Create database schema
- Create super admin account
- Prompt for secure password

**Save the super admin credentials securely!**

### Step 4: Install Windows Service

Run the service installation script as Administrator:

```powershell
cd C:\MailroomApp\scripts
.\install_service.ps1
```

**Options:**
- `-InstallPath`: Installation directory (default: C:\MailroomApp)
- `-ServiceName`: Service name (default: MailroomTracking)
- `-PythonPath`: Path to Python executable (default: C:\Python312\python.exe)
- `-Uninstall`: Uninstall the service

**Example:**
```powershell
# Install with defaults
.\install_service.ps1

# Install with custom path
.\install_service.ps1 -InstallPath "D:\Apps\Mailroom"

# Uninstall service
.\install_service.ps1 -Uninstall
```

The script will:
- Validate prerequisites (NSSM, Python, application files)
- Create Windows Service
- Configure automatic startup
- Set up logging
- Optionally start the service

### Step 5: Start the Service

```powershell
# Start service
Start-Service MailroomTracking

# Check status
Get-Service MailroomTracking

# View logs
Get-Content C:\MailroomApp\logs\service-stdout.log -Tail 50
```

### Step 6: Set Up HTTPS with Caddy (Recommended)

For production deployments, set up Caddy as an HTTPS reverse proxy:

```powershell
cd C:\MailroomApp\scripts
.\install_caddy.ps1
```

The script will:
- Install Caddy if not present
- Create self-signed certificates (or use existing)
- Configure HTTPS with security headers
- Install Caddy as a Windows Service
- Set up access logging

**For detailed Caddy configuration, see [Caddy Setup Guide](CADDY_SETUP.md)**

### Step 7: Verify Installation

1. **Check services are running:**
   ```powershell
   Get-Service MailroomTracking
   Get-Service CaddyMailroom  # If Caddy is installed
   # Status should be "Running"
   ```

2. **Test application access:**
   - With Caddy: https://mailroom.company.local
   - Without Caddy: http://localhost:8000
   - You should see the login page

3. **Log in with super admin:**
   - Use credentials created during database initialization
   - Change password after first login

4. **Configure DNS and Firewall:**
   - Add DNS entry for your domain
   - Configure firewall to allow HTTPS (port 443)

## Deployment Scripts

The `scripts\` directory contains PowerShell scripts for deployment and maintenance.

### install_service.ps1

Installs the application as a Windows Service using NSSM.

**Usage:**
```powershell
.\install_service.ps1 [options]
```

**Options:**
- `-InstallPath <path>`: Installation directory
- `-ServiceName <name>`: Service name
- `-PythonPath <path>`: Path to Python executable
- `-Uninstall`: Uninstall the service
- `-Help`: Display help message

**Features:**
- Validates prerequisites
- Creates Windows Service with NSSM
- Configures automatic startup
- Sets up stdout/stderr logging
- Configures service restart on failure

### init_database.ps1

Initializes the database and creates the super admin account.

**Usage:**
```powershell
.\init_database.ps1 [options]
```

**Options:**
- `-InstallPath <path>`: Installation directory
- `-PythonPath <path>`: Path to Python executable
- `-SuperAdminUsername <name>`: Super admin username
- `-SuperAdminPassword <pass>`: Super admin password (will prompt if not provided)
- `-SuperAdminFullName <name>`: Super admin full name
- `-ResetDatabase`: Delete existing database and recreate
- `-Help`: Display help message

**Features:**
- Validates Python and application installation
- Creates database schema
- Creates super admin account with secure password
- Prompts for password if not provided
- Validates password strength (min 12 characters)

### backup.ps1

Creates backups of the database and uploaded files.

**Usage:**
```powershell
.\backup.ps1 [options]
```

**Options:**
- `-InstallPath <path>`: Installation directory
- `-BackupPath <path>`: Backup destination directory
- `-SkipCompression`: Skip ZIP compression
- `-Help`: Display help message

**Features:**
- Backs up DuckDB database (including WAL files)
- Backs up uploaded files
- Backs up .env configuration
- Creates backup manifest
- Compresses backup to ZIP (optional)
- Shows disk space information

**Example:**
```powershell
# Create backup with defaults
.\backup.ps1

# Create backup to custom location
.\backup.ps1 -BackupPath "D:\Backups\Mailroom"

# Create uncompressed backup (faster)
.\backup.ps1 -SkipCompression
```

### cleanup_backups.ps1

Removes old backups based on retention policy.

**Usage:**
```powershell
.\cleanup_backups.ps1 [options]
```

**Options:**
- `-BackupPath <path>`: Backup directory to clean
- `-RetentionDays <days>`: Number of days to retain backups (default: 30)
- `-DryRun`: Show what would be deleted without actually deleting
- `-Force`: Skip confirmation prompt
- `-Help`: Display help message

**Features:**
- Finds backups older than retention period
- Shows backup details (age, size)
- Dry run mode for preview
- Confirmation prompt (unless -Force)
- Summary of deleted backups and freed space

**Example:**
```powershell
# Preview cleanup (dry run)
.\cleanup_backups.ps1 -DryRun

# Clean backups older than 30 days (default)
.\cleanup_backups.ps1

# Clean backups older than 90 days
.\cleanup_backups.ps1 -RetentionDays 90

# Clean without confirmation
.\cleanup_backups.ps1 -Force
```

## Service Management

### Basic Commands

```powershell
# Start service
Start-Service MailroomTracking

# Stop service
Stop-Service MailroomTracking

# Restart service
Restart-Service MailroomTracking

# Check status
Get-Service MailroomTracking

# View service details
Get-Service MailroomTracking | Format-List *
```

### View Logs

```powershell
# View stdout log (last 50 lines)
Get-Content C:\MailroomApp\logs\service-stdout.log -Tail 50

# View stderr log (errors)
Get-Content C:\MailroomApp\logs\service-stderr.log -Tail 50

# View application log
Get-Content C:\MailroomApp\logs\mailroom.log -Tail 50

# Follow log in real-time
Get-Content C:\MailroomApp\logs\mailroom.log -Wait -Tail 50
```

### Service Configuration

```powershell
# View service configuration
nssm dump MailroomTracking

# Edit service configuration
nssm edit MailroomTracking

# Change startup type
nssm set MailroomTracking Start SERVICE_AUTO_START
```

## Backup and Recovery

### Automated Backups

Set up scheduled task for daily backups:

```powershell
# Create scheduled task for daily backup at 2 AM
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\MailroomApp\scripts\backup.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 2am

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "MailroomBackup" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description "Daily backup of Mailroom Tracking System"
```

### Automated Cleanup

Set up scheduled task for weekly backup cleanup:

```powershell
# Create scheduled task for weekly cleanup on Sunday at 3 AM
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\MailroomApp\scripts\cleanup_backups.ps1 -Force"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "MailroomBackupCleanup" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description "Weekly cleanup of old Mailroom backups (30-day retention)"
```

### Manual Backup

```powershell
# Create immediate backup
cd C:\MailroomApp\scripts
.\backup.ps1
```

### Restore from Backup

1. **Stop the service:**
   ```powershell
   Stop-Service MailroomTracking
   ```

2. **Extract backup:**
   ```powershell
   # Extract ZIP backup
   Expand-Archive -Path "C:\Backups\Mailroom\mailroom_backup_20240115_020000.zip" `
       -DestinationPath "C:\Temp\restore"
   ```

3. **Restore database:**
   ```powershell
   # Backup current database (just in case)
   Copy-Item "C:\MailroomApp\data\mailroom.duckdb" `
       "C:\MailroomApp\data\mailroom.duckdb.old"
   
   # Restore database from backup
   Copy-Item "C:\Temp\restore\data\mailroom.duckdb" `
       "C:\MailroomApp\data\mailroom.duckdb" -Force
   ```

4. **Restore uploads:**
   ```powershell
   # Remove current uploads
   Remove-Item -Recurse -Force "C:\MailroomApp\uploads"
   
   # Restore uploads from backup
   Copy-Item -Recurse "C:\Temp\restore\uploads" `
       "C:\MailroomApp\uploads"
   ```

5. **Start the service:**
   ```powershell
   Start-Service MailroomTracking
   ```

6. **Verify restoration:**
   - Check service is running
   - Log in and verify data
   - Check recent packages and uploads

## Monitoring and Maintenance

### Health Checks

```powershell
# Check service status
Get-Service MailroomTracking

# Check if application is responding
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# Check disk space
Get-PSDrive C | Select-Object Used,Free
```

### Log Monitoring

Monitor logs for errors and warnings:

```powershell
# Check for errors in application log
Get-Content C:\MailroomApp\logs\mailroom.log | Select-String "ERROR"

# Check for warnings
Get-Content C:\MailroomApp\logs\mailroom.log | Select-String "WARNING"

# Check failed login attempts
Get-Content C:\MailroomApp\logs\mailroom.log | Select-String "login_failed"
```

### Database Maintenance

```powershell
# Check database size
Get-Item C:\MailroomApp\data\mailroom.duckdb | Select-Object Length

# Check WAL file size
Get-Item C:\MailroomApp\data\mailroom.duckdb.wal | Select-Object Length
```

### Performance Monitoring

Monitor system resources:

```powershell
# Check CPU and memory usage
Get-Process python | Select-Object CPU,WorkingSet

# Monitor in real-time
while ($true) {
    Clear-Host
    Get-Process python | Select-Object Name,CPU,WorkingSet,Threads
    Start-Sleep -Seconds 5
}
```

## Troubleshooting

### Service Won't Start

**Check service status:**
```powershell
Get-Service MailroomTracking
nssm status MailroomTracking
```

**Check logs:**
```powershell
Get-Content C:\MailroomApp\logs\service-stderr.log -Tail 50
```

**Common issues:**
- Python not found: Verify Python path in service configuration
- .env file missing: Create .env file from .env.example
- Port already in use: Change APP_PORT in .env
- Database locked: Ensure no other instances are running

### Application Errors

**Check application logs:**
```powershell
Get-Content C:\MailroomApp\logs\mailroom.log -Tail 100
```

**Common issues:**
- Database errors: Check database file permissions
- Upload errors: Check upload directory permissions
- Authentication errors: Verify SECRET_KEY is set

### Database Issues

**Database locked:**
```powershell
# Stop service
Stop-Service MailroomTracking

# Check for WAL file
Get-Item C:\MailroomApp\data\mailroom.duckdb.wal

# Start service
Start-Service MailroomTracking
```

**Database corruption:**
```powershell
# Restore from backup
.\scripts\backup.ps1  # Create current backup first
# Then restore from known good backup
```

### Permission Issues

**Fix file permissions:**
```powershell
# Grant service account full control
icacls "C:\MailroomApp" /grant "NT SERVICE\MailroomTracking:(OI)(CI)F" /T
```

### Network Issues

**Check if port is accessible:**
```powershell
Test-NetConnection -ComputerName localhost -Port 8000
```

**Check firewall:**
```powershell
# Add firewall rule
New-NetFirewallRule -DisplayName "Mailroom Tracking" `
    -Direction Inbound `
    -LocalPort 8000 `
    -Protocol TCP `
    -Action Allow
```

## Security Hardening

### File Permissions

Restrict access to sensitive directories:

```powershell
# Database directory
icacls "C:\MailroomApp\data" /grant "NT SERVICE\MailroomTracking:(OI)(CI)F" /inheritance:r

# Upload directory
icacls "C:\MailroomApp\uploads" /grant "NT SERVICE\MailroomTracking:(OI)(CI)F" /inheritance:r

# Log directory
icacls "C:\MailroomApp\logs" /grant "NT SERVICE\MailroomTracking:(OI)(CI)F" /inheritance:r

# Configuration file
icacls "C:\MailroomApp\.env" /grant "NT SERVICE\MailroomTracking:F" /inheritance:r
```

### Network Security

- Run behind reverse proxy (Caddy/nginx)
- Use HTTPS with valid TLS certificates
- Restrict access to internal network only
- Configure firewall rules

### Regular Maintenance

- Update Python and dependencies regularly
- Review audit logs for suspicious activity
- Test backup restoration quarterly
- Monitor disk space and performance
- Review and update passwords periodically

## Additional Resources

- [Configuration Guide](CONFIGURATION.md)
- [Caddy Setup Guide](CADDY_SETUP.md)
- [RBAC Implementation](RBAC_IMPLEMENTATION.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [NSSM Documentation](https://nssm.cc/usage)
- [Caddy Documentation](https://caddyserver.com/docs/)
