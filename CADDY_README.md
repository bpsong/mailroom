# Caddy Configuration Files (Windows)

This repository is documented for **Windows deployments** of the Mailroom Tracking System. Use the Windows Caddy configuration and PowerShell commands below.

## Files

### `Caddyfile.windows` (recommended)
Windows-first Caddy reverse proxy config with:
- HTTPS reverse proxy to FastAPI on `localhost:8000`
- TLS 1.2/1.3 with certificate path env vars
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- JSON access/error logging to `C:\MailroomApp\logs\`

### `Caddyfile`
Legacy non-Windows-optimized variant kept for compatibility. For Windows Server, prefer `Caddyfile.windows`.

## Quick Start (Windows)

1. Install Caddy:
   ```powershell
   choco install caddy
   ```

2. Use the Windows Caddyfile:
   ```powershell
   Copy-Item .\Caddyfile.windows .\Caddyfile -Force
   ```

3. Configure environment variables for TLS and host:
   ```powershell
   $env:DOMAIN='mailroom.company.local'
   $env:TLS_CERT_PATH='C:\MailroomApp\certs\cert.pem'
   $env:TLS_KEY_PATH='C:\MailroomApp\certs\key.pem'
   ```

4. Validate and run:
   ```powershell
   caddy validate --config Caddyfile --adapter caddyfile
   caddy run --config Caddyfile --adapter caddyfile
   ```

5. Verify backend connectivity:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
   ```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DOMAIN` | `mailroom.company.local` | HTTPS host name |
| `TLS_CERT_PATH` | `C:\MailroomApp\certs\cert.pem` | TLS certificate path |
| `TLS_KEY_PATH` | `C:\MailroomApp\certs\key.pem` | TLS private key path |

## Troubleshooting (Windows)

### Port 443 already in use
```powershell
netstat -ano | findstr :443
```

### Caddy config check fails
```powershell
caddy validate --config Caddyfile --adapter caddyfile
```

### Backend unreachable
```powershell
Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing
```

## Related Docs

- [docs/CADDY_SETUP.md](docs/CADDY_SETUP.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
