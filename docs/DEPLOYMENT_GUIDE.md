# Deployment Guide for Windows Server

## Overview

This guide provides step-by-step instructions for deploying the Mailroom Tracking System on Windows Server. The application runs as a Windows Service behind a Caddy reverse proxy for HTTPS termination.

**Target Environment**: Windows Server 2016+ (64-bit)  
**Prerequisites**: Administrator access, network connectivity  
**Deployment Time**: 30-60 minutes

## Architecture Overview

```
Internet/Intranet
       │
       ▼
┌─────────────────┐
│  Caddy (HTTPS)  │  Port 443
│  Reverse Proxy  │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  FastAPI App    │  Port 8000
│  (Uvicorn)      │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  DuckDB         │  File-based
│  Database       │
└─────────────────┘
```

## System Requirements

### Minimum Requirements

- **OS**: Windows Server 2016 or later (64-bit)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 20 GB free space
- **Network**: Static IP address or hostname

### Recommended Requirements

- **OS**: Windows Server 2019 or later (64-bit)
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 50 GB free space (SSD preferred)
- **Network**: Static IP with DNS entry

### Software Prerequisites

- **Python**: 3.12 or later
- **NSSM**: Non-Sucking Service Manager
- **Caddy**: 2.7 or later (optional, for HTTPS)
- **PowerShell**: 5.1 or later (included in Windows Server)

## Pre-Deployment Checklist

- [ ] Windows Server with administrator access
- [ ] Static IP address or hostname configured
- [ ] DNS entry created (if using custom domain)
- [ ] Firewall rules planned (ports 80, 443, 8000)
- [ ] TLS certificates obtained (or plan for self-signed)
- [ ] Backup strategy defined
- [ ] Service account created (optional but recommended)

## Installation Steps

### Step 1: Install Python

1. Download Python 3.12+ from [python.org](https://www.python.org/downloads/windows/)

2. Run the installer with these options:
   - ✅ Add Python to PATH
   - ✅ Install for all users
   - Installation directory: `C:\Python312`

3. Verify installation:
   ```powershell
   python --version
   # Should output: Python 3.12.x
   
   pip --version
   # Should output: pip 23.x.x
   ```

### Step 2: Install NSSM (Service Manager)

**Option A: Using Chocolatey** (recommended)

1. Install Chocolatey if not already installed:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. Install NSSM:
   ```powershell
   choco install nssm -y
   ```

**Option B: Manual Installation**

1. Download NSSM from [nssm.cc/download](https://nssm.cc/download)
2. Extract to `C:\Program Files\NSSM`
3. Add to system PATH:
   ```powershell
   $env:Path += ";C:\Program Files\NSSM\win64"
   [Environment]::SetEnvironmentVariable("Path", $env:Path, "Machine")
   ```

4. Verify installation:
   ```powershell
   nssm --version
   ```

### Step 3: Deploy Application Files

1. Create installation directory:
   ```powershell
   New-Item -ItemType Directory -Path "C:\MailroomApp" -Force
   ```

2. Copy application files to `C:\MailroomApp`:
   - All Python source files (`app/` directory)
   - Static files (`static/`, `templates/`)
   - Scripts (`scripts/`)
   - Configuration files (`Caddyfile`, `.env.example`)
   - Requirements file (`pyproject.toml` or `requirements.txt`)

3. Set directory permissions:
   ```powershell
   # Grant full control to service account or NETWORK SERVICE
   icacls "C:\MailroomApp" /grant "NETWORK SERVICE:(OI)(CI)F" /T
   ```

### Step 4: Install Python Dependencies

1. Navigate to installation directory:
   ```powershell
   cd C:\MailroomApp
   ```

2. Create virtual environment (optional but recommended):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -e .
   # Or if using requirements.txt:
   # pip install -r requirements.txt
   ```

4. Verify installation:
   ```powershell
   python -c "import fastapi; import duckdb; print('Dependencies OK')"
   ```

### Step 5: Configure Application

1. Copy environment template:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` file with your configuration:
   ```powershell
   notepad .env
   ```

3. **Required Configuration**:
   ```env
   # Application
   APP_ENV=production
   APP_HOST=0.0.0.0
   APP_PORT=8000
   SECRET_KEY=<generate-secure-random-key-min-32-chars>
   
   # Database
   DATABASE_PATH=./data/mailroom.duckdb
   
   # File Storage
   UPLOAD_DIR=./uploads
   MAX_UPLOAD_SIZE=5242880
   
   # Security
   SESSION_TIMEOUT=1800
   MAX_FAILED_LOGINS=5
   ACCOUNT_LOCKOUT_DURATION=1800
   PASSWORD_MIN_LENGTH=12
   
   # Domain (for HTTPS)
   DOMAIN=mailroom.company.local
   ```

4. Generate secure SECRET_KEY:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. Create required directories:
   ```powershell
   New-Item -ItemType Directory -Path "C:\MailroomApp\data" -Force
   New-Item -ItemType Directory -Path "C:\MailroomApp\uploads" -Force
   New-Item -ItemType Directory -Path "C:\MailroomApp\logs" -Force
   New-Item -ItemType Directory -Path "C:\MailroomApp\certs" -Force
   ```

### Step 6: Initialize Database

1. Run database initialization script:
   ```powershell
   cd C:\MailroomApp
   .\scripts\init_database.ps1
   ```

2. Follow prompts to create super admin account:
   - Username: `admin` (or custom)
   - Password: (minimum 12 characters, mixed case, symbols)
   - Full Name: `System Administrator`

3. Verify database creation:
   ```powershell
   Test-Path "C:\MailroomApp\data\mailroom.duckdb"
   # Should return: True
   ```

4. **IMPORTANT**: Save super admin credentials securely!

### Step 7: Install Application as Windows Service

1. Run service installation script:
   ```powershell
   cd C:\MailroomApp\scripts
   .\install_service.ps1
   ```

2. Or install manually with custom parameters:
   ```powershell
   .\install_service.ps1 `
       -InstallPath "C:\MailroomApp" `
       -ServiceName "MailroomTracking" `
       -PythonPath "C:\Python312\python.exe"
   ```

3. Verify service installation:
   ```powershell
   Get-Service MailroomTracking
   ```

4. Start the service:
   ```powershell
   Start-Service MailroomTracking
   ```

5. Check service status:
   ```powershell
   Get-Service MailroomTracking
   # Status should be: Running
   ```

6. Test application:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
   # Should return: {"status":"healthy",...}
   ```

### Step 8: Configure Firewall

1. Allow inbound traffic on required ports:
   ```powershell
   # Allow HTTP (for testing)
   New-NetFirewallRule -DisplayName "Mailroom HTTP" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   
   # Allow HTTPS (for production)
   New-NetFirewallRule -DisplayName "Mailroom HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
   ```

2. For production, remove HTTP rule after HTTPS is configured:
   ```powershell
   Remove-NetFirewallRule -DisplayName "Mailroom HTTP"
   ```

### Step 9: Install and Configure Caddy (HTTPS)

**Note**: This step is optional but strongly recommended for production.

1. Run Caddy installation script:
   ```powershell
   cd C:\MailroomApp\scripts
   .\install_caddy.ps1
   ```

2. Or install manually:
   ```powershell
   # Install Caddy
   choco install caddy -y
   
   # Verify installation
   caddy version
   ```

3. Configure Caddyfile:
   ```powershell
   notepad C:\MailroomApp\Caddyfile.windows
   ```

4. Example Caddyfile configuration:
   ```caddyfile
   mailroom.company.local {
       reverse_proxy localhost:8000
       
       tls C:\MailroomApp\certs\cert.pem C:\MailroomApp\certs\key.pem
       
       encode gzip
       
       log {
           output file C:\MailroomApp\logs\caddy-access.log
       }
       
       header {
           Strict-Transport-Security "max-age=31536000;"
           X-Content-Type-Options "nosniff"
           X-Frame-Options "DENY"
           X-XSS-Protection "1; mode=block"
       }
   }
   ```

5. Install Caddy as Windows Service:
   ```powershell
   nssm install CaddyMailroom "C:\ProgramData\chocolatey\bin\caddy.exe"
   nssm set CaddyMailroom AppDirectory "C:\MailroomApp"
   nssm set CaddyMailroom AppParameters "run --config Caddyfile.windows --adapter caddyfile"
   nssm set CaddyMailroom DisplayName "Caddy Reverse Proxy (Mailroom)"
   nssm set CaddyMailroom Start SERVICE_AUTO_START
   ```

6. Start Caddy service:
   ```powershell
   Start-Service CaddyMailroom
   ```

7. Verify HTTPS access:
   ```powershell
   Invoke-WebRequest -Uri "https://mailroom.company.local/health" -UseBasicParsing
   ```

### Step 10: Configure TLS Certificates

**Option A: Self-Signed Certificate** (for testing/internal use)

1. Generate self-signed certificate:
   ```powershell
   $cert = New-SelfSignedCertificate `
       -DnsName "mailroom.company.local" `
       -CertStoreLocation "Cert:\LocalMachine\My" `
       -KeyExportPolicy Exportable `
       -NotAfter (Get-Date).AddYears(5)
   
   # Export certificate
   $certPath = "C:\MailroomApp\certs\cert.pem"
   $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert) | Set-Content $certPath -Encoding Byte
   ```

**Option B: Internal CA Certificate** (recommended for production)

1. Request certificate from your internal Certificate Authority
2. Export certificate and private key in PEM format
3. Copy files to:
   - Certificate: `C:\MailroomApp\certs\cert.pem`
   - Private Key: `C:\MailroomApp\certs\key.pem`

4. Set file permissions:
   ```powershell
   icacls "C:\MailroomApp\certs\key.pem" /inheritance:r /grant:r "NETWORK SERVICE:R"
   ```

### Step 11: Configure Automated Backups

1. Create backup directory:
   ```powershell
   New-Item -ItemType Directory -Path "C:\Backups\Mailroom" -Force
   ```

2. Test backup script:
   ```powershell
   cd C:\MailroomApp\scripts
   .\backup.ps1
   ```

3. Schedule daily backups using Task Scheduler:
   ```powershell
   $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\MailroomApp\scripts\backup.ps1"
   $trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
   $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
   
   Register-ScheduledTask -TaskName "MailroomBackup" -Action $action -Trigger $trigger -Principal $principal -Description "Daily backup of Mailroom database"
   ```

4. Schedule backup cleanup (30-day retention):
   ```powershell
   $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\MailroomApp\scripts\cleanup_backups.ps1"
   $trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
   
   Register-ScheduledTask -TaskName "MailroomBackupCleanup" -Action $action -Trigger $trigger -Principal $principal -Description "Cleanup old Mailroom backups"
   ```

### Step 12: Verify Deployment

1. **Check Services**:
   ```powershell
   Get-Service MailroomTracking, CaddyMailroom | Format-Table Name, Status, StartType
   ```

2. **Test Health Endpoint**:
   ```powershell
   Invoke-RestMethod -Uri "https://mailroom.company.local/health"
   ```

3. **Test Login**:
   - Open browser: `https://mailroom.company.local`
   - Login with super admin credentials
   - Verify dashboard loads

4. **Check Logs**:
   ```powershell
   Get-Content "C:\MailroomApp\logs\mailroom.log" -Tail 50
   Get-Content "C:\MailroomApp\logs\service-stdout.log" -Tail 50
   ```

5. **Test Package Registration**:
   - Navigate to "Register Package"
   - Fill in test data
   - Upload photo
   - Verify package appears in list

## Post-Deployment Configuration

### Create Additional Users

1. Login as super admin
2. Navigate to "User Management"
3. Create admin accounts for mailroom supervisors
4. Create operator accounts for mailroom staff

### Import Recipients

1. Prepare CSV file with columns:
   - employee_id
   - name
   - email
   - department

2. Navigate to "Recipient Management" → "Import CSV"
3. Upload CSV file
4. Review validation report
5. Confirm import

### Configure DNS

1. Add DNS A record:
   ```
   mailroom.company.local → <server-ip-address>
   ```

2. Verify DNS resolution:
   ```powershell
   Resolve-DnsName mailroom.company.local
   ```

### Configure Email Notifications (Optional)

If implementing email notifications in the future:

1. Update `.env` with SMTP settings:
   ```env
   SMTP_HOST=smtp.company.local
   SMTP_PORT=587
   SMTP_USER=mailroom@company.com
   SMTP_PASSWORD=<password>
   SMTP_FROM=mailroom@company.com
   ```

2. Restart service:
   ```powershell
   Restart-Service MailroomTracking
   ```

## Monitoring and Maintenance

### Service Monitoring

**Check Service Status**:
```powershell
Get-Service MailroomTracking, CaddyMailroom
```

**View Service Logs**:
```powershell
# Application logs
Get-Content "C:\MailroomApp\logs\mailroom.log" -Tail 100 -Wait

# Service stdout/stderr
Get-Content "C:\MailroomApp\logs\service-stdout.log" -Tail 100 -Wait
Get-Content "C:\MailroomApp\logs\service-stderr.log" -Tail 100 -Wait
```

**Restart Services**:
```powershell
Restart-Service MailroomTracking
Restart-Service CaddyMailroom
```

### Database Maintenance

**Weekly Tasks**:
```powershell
# Vacuum database (reclaim space)
python -c "import duckdb; conn = duckdb.connect('C:/MailroomApp/data/mailroom.duckdb'); conn.execute('VACUUM'); conn.close()"
```

**Monthly Tasks**:
```powershell
# Analyze database (update statistics)
python -c "import duckdb; conn = duckdb.connect('C:/MailroomApp/data/mailroom.duckdb'); conn.execute('ANALYZE'); conn.close()"
```

### Log Rotation

Logs are automatically rotated by the application. Manual rotation if needed:

```powershell
# Archive old logs
Compress-Archive -Path "C:\MailroomApp\logs\mailroom.log" -DestinationPath "C:\MailroomApp\logs\archive\mailroom-$(Get-Date -Format 'yyyyMMdd').zip"

# Clear log file
Clear-Content "C:\MailroomApp\logs\mailroom.log"
```

### Disk Space Monitoring

```powershell
# Check disk space
Get-PSDrive C | Select-Object Used, Free

# Check database size
Get-ChildItem "C:\MailroomApp\data\mailroom.duckdb" | Select-Object Name, @{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB,2)}}

# Check uploads size
Get-ChildItem "C:\MailroomApp\uploads" -Recurse | Measure-Object -Property Length -Sum | Select-Object @{Name="Size(GB)";Expression={[math]::Round($_.Sum/1GB,2)}}
```

## Troubleshooting

### Service Won't Start

**Symptom**: Service fails to start or stops immediately

**Solutions**:
1. Check service logs:
   ```powershell
   Get-Content "C:\MailroomApp\logs\service-stderr.log" -Tail 50
   ```

2. Verify Python path:
   ```powershell
   Test-Path "C:\Python312\python.exe"
   ```

3. Test application manually:
   ```powershell
   cd C:\MailroomApp
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. Check .env configuration:
   ```powershell
   notepad C:\MailroomApp\.env
   ```

### Cannot Access Application

**Symptom**: Browser cannot connect to application

**Solutions**:
1. Verify services are running:
   ```powershell
   Get-Service MailroomTracking, CaddyMailroom
   ```

2. Check firewall rules:
   ```powershell
   Get-NetFirewallRule -DisplayName "*Mailroom*"
   ```

3. Test local connectivity:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 8000
   Test-NetConnection -ComputerName localhost -Port 443
   ```

4. Check DNS resolution:
   ```powershell
   Resolve-DnsName mailroom.company.local
   ```

### Database Locked Errors

**Symptom**: "database is locked" errors in logs

**Solutions**:
1. Restart application service:
   ```powershell
   Restart-Service MailroomTracking
   ```

2. Check for stale lock files:
   ```powershell
   Get-ChildItem "C:\MailroomApp\data" -Filter "*.wal"
   ```

3. Verify WAL mode is enabled (check logs on startup)

### High Memory Usage

**Symptom**: Application consuming excessive memory

**Solutions**:
1. Check number of active sessions:
   ```sql
   SELECT COUNT(*) FROM sessions WHERE expires_at > CURRENT_TIMESTAMP;
   ```

2. Clear expired sessions:
   ```sql
   DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;
   ```

3. Restart service to clear memory:
   ```powershell
   Restart-Service MailroomTracking
   ```

### Certificate Errors

**Symptom**: Browser shows certificate warnings

**Solutions**:
1. Verify certificate files exist:
   ```powershell
   Test-Path "C:\MailroomApp\certs\cert.pem"
   Test-Path "C:\MailroomApp\certs\key.pem"
   ```

2. Check certificate expiration:
   ```powershell
   $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("C:\MailroomApp\certs\cert.pem")
   $cert.NotAfter
   ```

3. For self-signed certificates, add to Trusted Root:
   ```powershell
   Import-Certificate -FilePath "C:\MailroomApp\certs\cert.pem" -CertStoreLocation Cert:\LocalMachine\Root
   ```

## Upgrading

### Application Upgrade Process

1. **Backup Current Installation**:
   ```powershell
   # Stop services
   Stop-Service MailroomTracking, CaddyMailroom
   
   # Backup database
   Copy-Item "C:\MailroomApp\data\mailroom.duckdb" "C:\Backups\Mailroom\pre-upgrade-$(Get-Date -Format 'yyyyMMdd').duckdb"
   
   # Backup application
   Compress-Archive -Path "C:\MailroomApp" -DestinationPath "C:\Backups\Mailroom\app-backup-$(Get-Date -Format 'yyyyMMdd').zip"
   ```

2. **Deploy New Version**:
   ```powershell
   # Copy new files (preserve .env and data/)
   Copy-Item -Path "\\deploy-server\mailroom\*" -Destination "C:\MailroomApp" -Recurse -Force -Exclude ".env","data","uploads"
   ```

3. **Update Dependencies**:
   ```powershell
   cd C:\MailroomApp
   pip install -e . --upgrade
   ```

4. **Run Migrations** (if any):
   ```powershell
   python -m app.database.migrations
   ```

5. **Start Services**:
   ```powershell
   Start-Service MailroomTracking, CaddyMailroom
   ```

6. **Verify Upgrade**:
   ```powershell
   Invoke-RestMethod -Uri "https://mailroom.company.local/health"
   ```

### Rollback Procedure

If upgrade fails:

1. **Stop Services**:
   ```powershell
   Stop-Service MailroomTracking, CaddyMailroom
   ```

2. **Restore Application**:
   ```powershell
   Remove-Item "C:\MailroomApp\*" -Recurse -Force -Exclude ".env"
   Expand-Archive -Path "C:\Backups\Mailroom\app-backup-<date>.zip" -DestinationPath "C:\MailroomApp" -Force
   ```

3. **Restore Database**:
   ```powershell
   Copy-Item "C:\Backups\Mailroom\pre-upgrade-<date>.duckdb" "C:\MailroomApp\data\mailroom.duckdb" -Force
   ```

4. **Start Services**:
   ```powershell
   Start-Service MailroomTracking, CaddyMailroom
   ```

## Security Hardening

### Service Account

Create dedicated service account (recommended for production):

1. Create service account:
   ```powershell
   $password = ConvertTo-SecureString "SecurePassword123!" -AsPlainText -Force
   New-LocalUser -Name "MailroomService" -Password $password -Description "Mailroom Tracking Service Account" -PasswordNeverExpires
   ```

2. Grant permissions:
   ```powershell
   icacls "C:\MailroomApp" /grant "MailroomService:(OI)(CI)F" /T
   ```

3. Update service to use account:
   ```powershell
   nssm set MailroomTracking ObjectName ".\MailroomService" "<password>"
   ```

### File System Permissions

Restrict access to sensitive files:

```powershell
# .env file - read-only for service account
icacls "C:\MailroomApp\.env" /inheritance:r /grant:r "MailroomService:R"

# Database - full control for service account only
icacls "C:\MailroomApp\data" /inheritance:r /grant:r "MailroomService:(OI)(CI)F"

# Certificates - read-only for service account
icacls "C:\MailroomApp\certs" /inheritance:r /grant:r "MailroomService:R"
```

### Network Security

1. **Restrict Port Access**:
   ```powershell
   # Remove public access to port 8000
   Remove-NetFirewallRule -DisplayName "Mailroom HTTP"
   
   # Only allow HTTPS (443)
   New-NetFirewallRule -DisplayName "Mailroom HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
   ```

2. **Enable Windows Firewall Logging**:
   ```powershell
   Set-NetFirewallProfile -Profile Domain,Public,Private -LogAllowed True -LogBlocked True -LogFileName "C:\Windows\System32\LogFiles\Firewall\pfirewall.log"
   ```

### Audit Logging

Enable Windows audit logging for service:

```powershell
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
```

## Performance Tuning

### Application Settings

Optimize `.env` for production:

```env
# Increase checkpoint interval for better write performance
DATABASE_CHECKPOINT_INTERVAL=600

# Adjust rate limits based on usage
RATE_LIMIT_LOGIN=20
RATE_LIMIT_API=200

# Enable production optimizations
APP_ENV=production
```

### Windows Server Optimization

1. **Disable unnecessary services**:
   ```powershell
   Get-Service | Where-Object {$_.Status -eq "Running" -and $_.StartType -eq "Automatic"} | Select-Object Name, DisplayName
   ```

2. **Configure power plan**:
   ```powershell
   powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  # High Performance
   ```

3. **Optimize network settings**:
   ```powershell
   Set-NetTCPSetting -SettingName InternetCustom -AutoTuningLevelLocal Normal
   ```

## Disaster Recovery

### Backup Strategy

**Daily Backups**:
- Database file
- Uploaded photos
- Configuration files

**Weekly Backups**:
- Full application directory
- Windows Service configuration

**Monthly Backups**:
- System state
- Complete server backup

### Recovery Procedures

**Database Recovery**:
```powershell
# Stop service
Stop-Service MailroomTracking

# Restore database
Copy-Item "C:\Backups\Mailroom\<date>\mailroom.duckdb" "C:\MailroomApp\data\mailroom.duckdb" -Force

# Start service
Start-Service MailroomTracking
```

**Full System Recovery**:
1. Install Windows Server
2. Install Python, NSSM, Caddy
3. Restore application files from backup
4. Restore database from backup
5. Install and start services
6. Verify functionality

## Support and Resources

### Log Locations

- Application logs: `C:\MailroomApp\logs\mailroom.log`
- Service stdout: `C:\MailroomApp\logs\service-stdout.log`
- Service stderr: `C:\MailroomApp\logs\service-stderr.log`
- Caddy logs: `C:\MailroomApp\logs\caddy-access.log`
- Windows Event Log: Event Viewer → Windows Logs → Application

### Useful Commands

```powershell
# Service management
Get-Service MailroomTracking
Start-Service MailroomTracking
Stop-Service MailroomTracking
Restart-Service MailroomTracking

# View logs
Get-Content "C:\MailroomApp\logs\mailroom.log" -Tail 100 -Wait

# Check health
Invoke-RestMethod -Uri "https://mailroom.company.local/health"

# Database size
Get-ChildItem "C:\MailroomApp\data\mailroom.duckdb" | Select-Object Name, Length

# Service configuration
nssm dump MailroomTracking
```

### Documentation

- API Documentation: `https://mailroom.company.local/docs`
- User Guides: `C:\MailroomApp\docs\`
- Database Schema: `C:\MailroomApp\docs\DATABASE_SCHEMA.md`
- Configuration Reference: `C:\MailroomApp\docs\CONFIGURATION.md`

## Appendix

### A. Complete .env Template

See `.env.example` in application directory or refer to `docs/CONFIGURATION.md`

### B. Caddyfile Template

See `Caddyfile.windows` in application directory

### C. Service Installation Script

See `scripts/install_service.ps1` in application directory

### D. Backup Script

See `scripts/backup.ps1` in application directory

### E. Database Initialization Script

See `scripts/init_database.ps1` in application directory
