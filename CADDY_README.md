# Caddy Configuration Files

This directory contains Caddy reverse proxy configuration files for the Mailroom Tracking System.

## Files

### Caddyfile
Generic Caddyfile for Linux/Unix systems with standard paths.

**Features:**
- HTTPS reverse proxy to FastAPI (port 8000)
- TLS 1.2/1.3 support with custom certificates
- Comprehensive security headers (HSTS, CSP, X-Frame-Options, etc.)
- Access and error logging in JSON format
- Gzip/Zstd compression
- Health checks every 30 seconds
- Graceful error handling

**Paths:**
- Logs: `/var/log/caddy/`
- Certificates: `./certs/`

### Caddyfile.windows
Windows-specific Caddyfile with Windows paths.

**Features:**
- Same features as generic Caddyfile
- Windows-compatible paths (C:\MailroomApp\)
- Optimized for Windows Server deployment

**Paths:**
- Logs: `C:\MailroomApp\logs\`
- Certificates: `C:\MailroomApp\certs\`

## Quick Start

### Windows

1. **Install Caddy:**
   ```powershell
   choco install caddy
   ```

2. **Run installation script:**
   ```powershell
   cd scripts
   .\install_caddy.ps1
   ```

3. **Access application:**
   ```
   https://mailroom.company.local
   ```

### Linux/Unix

1. **Install Caddy:**
   ```bash
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update
   sudo apt install caddy
   ```

2. **Copy Caddyfile:**
   ```bash
   sudo cp Caddyfile /etc/caddy/Caddyfile
   ```

3. **Set environment variables:**
   ```bash
   export DOMAIN=mailroom.company.local
   export TLS_CERT_PATH=/etc/caddy/certs/cert.pem
   export TLS_KEY_PATH=/etc/caddy/certs/key.pem
   ```

4. **Start Caddy:**
   ```bash
   sudo systemctl start caddy
   sudo systemctl enable caddy
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `mailroom.company.local` | Domain name for HTTPS |
| `TLS_CERT_PATH` | Platform-specific | Path to TLS certificate |
| `TLS_KEY_PATH` | Platform-specific | Path to TLS private key |

### Security Headers

The Caddyfile includes these security headers:

- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-XSS-Protection**: Enables XSS filter
- **Strict-Transport-Security**: Forces HTTPS (HSTS)
- **Content-Security-Policy**: Restricts resource loading
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Disables unnecessary browser features

### TLS Configuration

- **Protocols**: TLS 1.2 and TLS 1.3
- **Certificates**: Custom certificates (internal CA or self-signed)
- **OCSP Stapling**: Disabled (for internal certificates)

## Customization

### Change Domain

Edit environment variable or Caddyfile:
```caddyfile
your-domain.com {
    # ... configuration
}
```

### Use Let's Encrypt

For public domains, enable automatic HTTPS:

1. Comment out custom TLS line
2. Add email for Let's Encrypt notifications
3. Enable auto_https in global options

```caddyfile
{$DOMAIN} {
    # tls {$TLS_CERT_PATH} {$TLS_KEY_PATH}  # Comment this out
    tls admin@company.com  # Add this
    
    # ... rest of configuration
}

{
    email admin@company.com
    auto_https on  # Change from off
}
```

### Adjust Logging

Change log level or format:
```caddyfile
log {
    level WARN  # Change from INFO
    format console  # Change from json
}
```

### Add Custom Headers

Add to the header block:
```caddyfile
header {
    # Existing headers...
    
    # Add custom header
    X-Custom-Header "value"
}
```

## Troubleshooting

### Validate Configuration

```bash
# Linux/Unix
caddy validate --config Caddyfile --adapter caddyfile

# Windows
caddy validate --config Caddyfile.windows --adapter caddyfile
```

### Test Configuration

```bash
# Linux/Unix
caddy run --config Caddyfile --adapter caddyfile

# Windows
caddy run --config Caddyfile.windows --adapter caddyfile
```

### Common Issues

**Port 443 already in use:**
```bash
# Check what's using port 443
netstat -tulpn | grep :443  # Linux
netstat -ano | findstr :443  # Windows
```

**Certificate errors:**
- Verify certificate paths are correct
- Check file permissions
- Ensure certificate matches domain

**Backend connection failed:**
- Verify FastAPI is running on port 8000
- Check firewall rules
- Test: `curl http://localhost:8000`

## Documentation

For detailed setup and configuration instructions, see:
- [Caddy Setup Guide](docs/CADDY_SETUP.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Configuration Guide](docs/CONFIGURATION.md)

## Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddyfile Syntax](https://caddyserver.com/docs/caddyfile)
- [Reverse Proxy Directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [TLS Directive](https://caddyserver.com/docs/caddyfile/directives/tls)
- [Security Headers Guide](https://securityheaders.com/)

