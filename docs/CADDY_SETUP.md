# Caddy Reverse Proxy Setup Guide

This document provides instructions for setting up Caddy as an HTTPS reverse proxy for the Mailroom Tracking System.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [TLS Certificates](#tls-certificates)
- [Service Management](#service-management)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Overview

Caddy serves as a reverse proxy that:
- Provides HTTPS encryption with TLS 1.2/1.3
- Adds security headers to all responses
- Handles access and error logging
- Compresses responses for better performance
- Forwards requests to the FastAPI application

## Prerequisites

### System Requirements

- Windows Server 2016 or later
- Administrator privileges
- NSSM (Non-Sucking Service Manager)
- Mailroom Tracking System installed and running

### Network Requirements

- Port 443 (HTTPS) accessible on the network
- DNS entry for your domain pointing to the server
- Firewall configured to allow HTTPS traffic

## Installation

### Option 1: Automated Installation (Recommended)

Use the provided PowerShell script:

```powershell
cd C:\MailroomApp\scripts
.\install_caddy.ps1
```

The script will:
1. Check for prerequisites (NSSM, Caddy)
2. Download Caddy if not installed
3. Create self-signed certificates if needed
4. Install Caddy as a Windows Service
5. Configure automatic startup

**Options:**
```powershell
# Install with custom paths
.\install_caddy.ps1 -InstallPath "D:\Apps\Mailroom" -CaddyPath "D:\Caddy"

# Uninstall Caddy service
.\install_caddy.ps1 -Uninstall

# Display help
.\install_caddy.ps1 -Help
```

### Option 2: Manual Installation

#### Step 1: Install Caddy

**Using Chocolatey:**
```powershell
choco install caddy
```

**Manual Download:**
1. Download from: https://caddyserver.com/download
2. Extract `caddy.exe` to `C:\Caddy`
3. Add `C:\Caddy` to system PATH

#### Step 2: Verify Installation

```powershell
caddy version
```

#### Step 3: Copy Caddyfile

```powershell
# Copy Windows-specific Caddyfile
Copy-Item C:\MailroomApp\Caddyfile.windows C:\MailroomApp\Caddyfile
```

#### Step 4: Install as Windows Service

```powershell
# Install service with NSSM
nssm install CaddyMailroom "C:\Caddy\caddy.exe"
nssm set CaddyMailroom AppDirectory "C:\MailroomApp"
nssm set CaddyMailroom AppParameters "run --config `"C:\MailroomApp\Caddyfile`" --adapter caddyfile"
nssm set CaddyMailroom DisplayName "Caddy Reverse Proxy (Mailroom)"
nssm set CaddyMailroom Description "HTTPS reverse proxy for Mailroom Tracking System"
nssm set CaddyMailroom Start SERVICE_AUTO_START

# Set environment variables
nssm set CaddyMailroom AppEnvironmentExtra "DOMAIN=mailroom.company.local" "TLS_CERT_PATH=C:\MailroomApp\certs\cert.pem" "TLS_KEY_PATH=C:\MailroomApp\certs\key.pem"

# Set up logging
nssm set CaddyMailroom AppStdout "C:\MailroomApp\logs\caddy-stdout.log"
nssm set CaddyMailroom AppStderr "C:\MailroomApp\logs\caddy-stderr.log"

# Start service
Start-Service CaddyMailroom
```

## Configuration

### Caddyfile Structure

The Caddyfile is located at `C:\MailroomApp\Caddyfile` (or `Caddyfile.windows`).

#### Main Configuration Sections

**1. Reverse Proxy**
```caddyfile
reverse_proxy localhost:8000 {
    health_uri /health
    health_interval 30s
    health_timeout 5s
}
```
- Forwards requests to FastAPI on port 8000
- Performs health checks every 30 seconds
- Forwards client IP and protocol headers

**2. TLS Configuration**
```caddyfile
tls {$TLS_CERT_PATH} {$TLS_KEY_PATH} {
    protocols tls1.2 tls1.3
}
```
- Uses custom TLS certificates
- Supports TLS 1.2 and 1.3
- Certificates configured via environment variables

**3. Security Headers**
```caddyfile
header {
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    X-XSS-Protection "1; mode=block"
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    Content-Security-Policy "..."
    # ... more headers
}
```
- Prevents clickjacking, XSS, MIME sniffing
- Enforces HTTPS with HSTS
- Implements Content Security Policy

**4. Logging**
```caddyfile
log {
    output file C:\MailroomApp\logs\caddy-access.log {
        roll_size 100mb
        roll_keep 10
        roll_keep_for 90d
    }
    format json
}
```
- JSON-formatted logs
- Automatic rotation at 100MB
- Keeps 10 files, retains for 90 days

### Environment Variables

Configure these in the service or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `mailroom.company.local` | Domain name for HTTPS |
| `TLS_CERT_PATH` | `C:\MailroomApp\certs\cert.pem` | Path to TLS certificate |
| `TLS_KEY_PATH` | `C:\MailroomApp\certs\key.pem` | Path to TLS private key |

### Customization

#### Change Domain

Edit `.env` file:
```env
DOMAIN=mailroom.yourcompany.com
```

Restart Caddy service:
```powershell
Restart-Service CaddyMailroom
```

#### Adjust Security Headers

Edit `Caddyfile` and modify the `header` block:
```caddyfile
header {
    # Add or modify headers
    X-Custom-Header "value"
}
```

#### Enable Automatic HTTPS (Let's Encrypt)

For public domains, use automatic HTTPS:

1. Edit `Caddyfile`:
```caddyfile
# Comment out custom TLS line
# tls {$TLS_CERT_PATH} {$TLS_KEY_PATH}

# Add email for Let's Encrypt
tls {$ADMIN_EMAIL:admin@company.local}
```

2. Update global options:
```caddyfile
{
    email admin@company.local
    auto_https on
}
```

## TLS Certificates

### Option 1: Self-Signed Certificates (Development/Testing)

The installation script creates self-signed certificates automatically.

**Manual creation:**
```powershell
# Create certificate directory
New-Item -ItemType Directory -Path "C:\MailroomApp\certs" -Force

# Generate self-signed certificate
$cert = New-SelfSignedCertificate `
    -DnsName "mailroom.company.local" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -NotAfter (Get-Date).AddYears(5)

# Export to PEM format (requires OpenSSL or manual conversion)
```

**Note:** Self-signed certificates will show browser warnings. Use for testing only.

### Option 2: Internal CA Certificates (Recommended for Production)

Request certificates from your organization's Certificate Authority:

1. **Generate Certificate Signing Request (CSR)**
2. **Submit CSR to your CA**
3. **Receive certificate and private key**
4. **Copy to server:**
   ```powershell
   Copy-Item cert.pem C:\MailroomApp\certs\cert.pem
   Copy-Item key.pem C:\MailroomApp\certs\key.pem
   ```
5. **Restart Caddy:**
   ```powershell
   Restart-Service CaddyMailroom
   ```

### Option 3: Let's Encrypt (Public Domains Only)

For public internet-facing domains:

1. Ensure port 80 and 443 are accessible from the internet
2. Configure automatic HTTPS in Caddyfile (see above)
3. Caddy will automatically obtain and renew certificates

### Certificate Permissions

Ensure proper file permissions:
```powershell
# Restrict access to certificates
icacls "C:\MailroomApp\certs" /grant "NT SERVICE\CaddyMailroom:(OI)(CI)R" /inheritance:r
icacls "C:\MailroomApp\certs" /grant "Administrators:(OI)(CI)F"
```

## Service Management

### Basic Commands

```powershell
# Start service
Start-Service CaddyMailroom

# Stop service
Stop-Service CaddyMailroom

# Restart service
Restart-Service CaddyMailroom

# Check status
Get-Service CaddyMailroom

# View service details
Get-Service CaddyMailroom | Format-List *
```

### View Logs

```powershell
# Access log (last 50 lines)
Get-Content C:\MailroomApp\logs\caddy-access.log -Tail 50

# Error log
Get-Content C:\MailroomApp\logs\caddy-error.log -Tail 50

# Service stdout
Get-Content C:\MailroomApp\logs\caddy-stdout.log -Tail 50

# Service stderr
Get-Content C:\MailroomApp\logs\caddy-stderr.log -Tail 50

# Follow logs in real-time
Get-Content C:\MailroomApp\logs\caddy-access.log -Wait -Tail 50
```

### Reload Configuration

After modifying Caddyfile:

```powershell
# Graceful reload (no downtime)
Restart-Service CaddyMailroom
```

### Test Configuration

Before restarting, validate Caddyfile syntax:

```powershell
cd C:\MailroomApp
caddy validate --config Caddyfile --adapter caddyfile
```

## Troubleshooting

### Service Won't Start

**Check service status:**
```powershell
Get-Service CaddyMailroom
nssm status CaddyMailroom
```

**Check error logs:**
```powershell
Get-Content C:\MailroomApp\logs\caddy-stderr.log -Tail 50
```

**Common issues:**
- **Port 443 already in use:** Another service is using HTTPS port
  ```powershell
  netstat -ano | findstr :443
  ```
- **Certificate not found:** Check TLS_CERT_PATH and TLS_KEY_PATH
- **Invalid Caddyfile:** Validate syntax with `caddy validate`
- **Permission denied:** Ensure service account has read access to certificates

### Cannot Access HTTPS Site

**Check if Caddy is running:**
```powershell
Get-Service CaddyMailroom
```

**Check if port 443 is listening:**
```powershell
netstat -ano | findstr :443
```

**Check firewall:**
```powershell
# Add firewall rule
New-NetFirewallRule -DisplayName "Caddy HTTPS" `
    -Direction Inbound `
    -LocalPort 443 `
    -Protocol TCP `
    -Action Allow
```

**Check DNS:**
```powershell
nslookup mailroom.company.local
```

**Test from server:**
```powershell
# Test HTTPS (ignore certificate warnings)
Invoke-WebRequest -Uri "https://mailroom.company.local" -SkipCertificateCheck
```

### Certificate Errors

**Browser shows "Not Secure":**
- Using self-signed certificate: Expected for development
- Certificate expired: Renew certificate
- Certificate hostname mismatch: Ensure certificate CN matches domain

**Check certificate details:**
```powershell
# View certificate
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("C:\MailroomApp\certs\cert.pem")
$cert | Format-List *
```

### Backend Connection Errors (502/503)

**Check if Mailroom service is running:**
```powershell
Get-Service MailroomTracking
```

**Test backend directly:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing
```

**Check Caddy logs:**
```powershell
Get-Content C:\MailroomApp\logs\caddy-error.log -Tail 50
```

### High Memory/CPU Usage

**Check Caddy process:**
```powershell
Get-Process caddy | Select-Object CPU,WorkingSet
```

**Reduce logging verbosity:**
Edit Caddyfile and change log level:
```caddyfile
log {
    level WARN  # Change from INFO to WARN or ERROR
}
```

## Security Considerations

### Security Headers Explained

| Header | Purpose | Value |
|--------|---------|-------|
| `X-Frame-Options` | Prevents clickjacking | `DENY` |
| `X-Content-Type-Options` | Prevents MIME sniffing | `nosniff` |
| `X-XSS-Protection` | Enables XSS filter | `1; mode=block` |
| `Strict-Transport-Security` | Forces HTTPS | `max-age=31536000` |
| `Content-Security-Policy` | Controls resource loading | Restricts to self + HTMX CDN |
| `Referrer-Policy` | Controls referrer information | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Controls browser features | Disables unnecessary features |

### Best Practices

1. **Use Strong TLS Configuration**
   - TLS 1.2 minimum (TLS 1.3 preferred)
   - Strong cipher suites (Caddy defaults are good)

2. **Keep Certificates Secure**
   - Restrict file permissions
   - Store private keys securely
   - Never commit to version control

3. **Monitor Logs**
   - Review access logs for suspicious activity
   - Set up alerts for error spikes
   - Rotate logs regularly

4. **Regular Updates**
   - Keep Caddy updated
   - Monitor security advisories
   - Test updates in staging first

5. **Network Security**
   - Run behind corporate firewall
   - Restrict access to internal network
   - Use VPN for remote access

### Hardening Checklist

- [ ] TLS 1.2+ only (no TLS 1.0/1.1)
- [ ] Valid certificates from trusted CA
- [ ] HSTS enabled with long max-age
- [ ] Security headers configured
- [ ] Admin API disabled (`admin off`)
- [ ] Logs configured and monitored
- [ ] File permissions restricted
- [ ] Firewall rules configured
- [ ] Regular security updates applied

## Additional Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddyfile Syntax](https://caddyserver.com/docs/caddyfile)
- [TLS Configuration](https://caddyserver.com/docs/caddyfile/directives/tls)
- [Reverse Proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Security Headers](https://securityheaders.com/)
- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)

