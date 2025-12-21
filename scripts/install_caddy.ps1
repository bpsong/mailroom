# Install and configure Caddy reverse proxy for Mailroom Tracking System
# This script installs Caddy as a Windows Service and configures HTTPS

param(
    [string]$InstallPath = "C:\MailroomApp",
    [string]$CaddyPath = "C:\Caddy",
    [string]$ServiceName = "CaddyMailroom",
    [switch]$Uninstall,
    [switch]$Help
)

# Display help
if ($Help) {
    Write-Host @"
Install and configure Caddy reverse proxy for Mailroom Tracking System

USAGE:
    .\install_caddy.ps1 [options]

OPTIONS:
    -InstallPath <path>    Installation directory (default: C:\MailroomApp)
    -CaddyPath <path>      Caddy installation directory (default: C:\Caddy)
    -ServiceName <name>    Service name (default: CaddyMailroom)
    -Uninstall             Uninstall the Caddy service
    -Help                  Display this help message

EXAMPLES:
    # Install Caddy with defaults
    .\install_caddy.ps1

    # Install with custom paths
    .\install_caddy.ps1 -InstallPath "D:\Apps\Mailroom" -CaddyPath "D:\Caddy"

    # Uninstall Caddy service
    .\install_caddy.ps1 -Uninstall

REQUIREMENTS:
    - Administrator privileges
    - NSSM (Non-Sucking Service Manager)
    - Mailroom application installed
    - TLS certificates (or will create self-signed)

"@
    exit 0
}

# Check for administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires administrator privileges" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
    exit 1
}

# Uninstall service
if ($Uninstall) {
    Write-Host "Uninstalling Caddy service..." -ForegroundColor Cyan
    
    # Check if service exists
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        # Stop service if running
        if ($service.Status -eq "Running") {
            Write-Host "Stopping service..."
            Stop-Service -Name $ServiceName -Force
            Start-Sleep -Seconds 2
        }
        
        # Remove service
        Write-Host "Removing service..."
        nssm remove $ServiceName confirm
        
        Write-Host "Caddy service uninstalled successfully" -ForegroundColor Green
    } else {
        Write-Host "Service '$ServiceName' not found" -ForegroundColor Yellow
    }
    
    exit 0
}

Write-Host "=== Caddy Installation for Mailroom Tracking System ===" -ForegroundColor Cyan
Write-Host ""

# Validate prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check for NSSM
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    Write-Host "ERROR: NSSM (Non-Sucking Service Manager) not found" -ForegroundColor Red
    Write-Host "Install NSSM using one of these methods:" -ForegroundColor Yellow
    Write-Host "  1. Chocolatey: choco install nssm" -ForegroundColor White
    Write-Host "  2. Download from: https://nssm.cc/download" -ForegroundColor White
    exit 1
}
Write-Host "  [OK] NSSM found: $($nssmPath.Source)" -ForegroundColor Green

# Check if Caddy is installed
$caddyExe = Get-Command caddy -ErrorAction SilentlyContinue
if (-not $caddyExe) {
    Write-Host "  [!] Caddy not found in PATH" -ForegroundColor Yellow
    Write-Host "Attempting to download Caddy..." -ForegroundColor Yellow
    
    # Create Caddy directory
    if (-not (Test-Path $CaddyPath)) {
        New-Item -ItemType Directory -Path $CaddyPath -Force | Out-Null
    }
    
    # Download Caddy
    $caddyUrl = "https://caddyserver.com/api/download?os=windows&arch=amd64"
    $caddyZip = Join-Path $env:TEMP "caddy.zip"
    $caddyExePath = Join-Path $CaddyPath "caddy.exe"
    
    try {
        Write-Host "  Downloading Caddy from $caddyUrl..."
        Invoke-WebRequest -Uri $caddyUrl -OutFile $caddyZip -UseBasicParsing
        
        Write-Host "  Extracting Caddy..."
        Expand-Archive -Path $caddyZip -DestinationPath $CaddyPath -Force
        Remove-Item $caddyZip
        
        # Add to PATH
        $envPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($envPath -notlike "*$CaddyPath*") {
            [Environment]::SetEnvironmentVariable("Path", "$envPath;$CaddyPath", "Machine")
            $env:Path = "$env:Path;$CaddyPath"
        }
        
        Write-Host "  [OK] Caddy installed: $caddyExePath" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to download Caddy: $_" -ForegroundColor Red
        Write-Host "Please install Caddy manually:" -ForegroundColor Yellow
        Write-Host "  1. Chocolatey: choco install caddy" -ForegroundColor White
        Write-Host "  2. Download from: https://caddyserver.com/download" -ForegroundColor White
        exit 1
    }
} else {
    Write-Host "  [OK] Caddy found: $($caddyExe.Source)" -ForegroundColor Green
    $caddyExePath = $caddyExe.Source
}

# Check if Mailroom app is installed
if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Mailroom application not found at: $InstallPath" -ForegroundColor Red
    Write-Host "Please install the Mailroom application first" -ForegroundColor Yellow
    exit 1
}
Write-Host "  [OK] Mailroom application found: $InstallPath" -ForegroundColor Green

# Check for Caddyfile
$caddyfile = Join-Path $InstallPath "Caddyfile.windows"
if (-not (Test-Path $caddyfile)) {
    $caddyfile = Join-Path $InstallPath "Caddyfile"
    if (-not (Test-Path $caddyfile)) {
        Write-Host "ERROR: Caddyfile not found in: $InstallPath" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  [OK] Caddyfile found: $caddyfile" -ForegroundColor Green

# Check for .env file
$envFile = Join-Path $InstallPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found" -ForegroundColor Yellow
    Write-Host "Using default configuration values" -ForegroundColor Yellow
}

# Load environment variables
$domain = "mailroom.company.local"
$certPath = Join-Path $InstallPath "certs\cert.pem"
$keyPath = Join-Path $InstallPath "certs\key.pem"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^DOMAIN=(.+)$') {
            $domain = $matches[1]
        }
        if ($_ -match '^TLS_CERT_PATH=(.+)$') {
            $certPath = $matches[1]
        }
        if ($_ -match '^TLS_KEY_PATH=(.+)$') {
            $keyPath = $matches[1]
        }
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Domain: $domain"
Write-Host "  Certificate: $certPath"
Write-Host "  Private Key: $keyPath"
Write-Host ""

# Check for TLS certificates
$certsDir = Join-Path $InstallPath "certs"
if (-not (Test-Path $certPath) -or -not (Test-Path $keyPath)) {
    Write-Host "TLS certificates not found. Creating self-signed certificate..." -ForegroundColor Yellow
    
    # Create certs directory
    if (-not (Test-Path $certsDir)) {
        New-Item -ItemType Directory -Path $certsDir -Force | Out-Null
    }
    
    # Generate self-signed certificate
    try {
        $cert = New-SelfSignedCertificate `
            -DnsName $domain `
            -CertStoreLocation "Cert:\LocalMachine\My" `
            -KeyExportPolicy Exportable `
            -KeySpec Signature `
            -KeyLength 2048 `
            -KeyAlgorithm RSA `
            -HashAlgorithm SHA256 `
            -NotAfter (Get-Date).AddYears(5)
        
        # Export certificate
        $certPassword = ConvertTo-SecureString -String "temp" -Force -AsPlainText
        $pfxPath = Join-Path $certsDir "temp.pfx"
        Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $certPassword | Out-Null
        
        # Convert to PEM format using OpenSSL (if available) or .NET
        $certPem = "-----BEGIN CERTIFICATE-----`n"
        $certPem += [Convert]::ToBase64String($cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert), [System.Base64FormattingOptions]::InsertLineBreaks)
        $certPem += "`n-----END CERTIFICATE-----"
        
        Set-Content -Path $certPath -Value $certPem
        
        Write-Host "  [OK] Self-signed certificate created" -ForegroundColor Green
        Write-Host "  WARNING: Self-signed certificates are not trusted by browsers" -ForegroundColor Yellow
        Write-Host "  For production, use certificates from your internal CA" -ForegroundColor Yellow
        
        # Clean up
        Remove-Item $pfxPath -Force
        Remove-Item "Cert:\LocalMachine\My\$($cert.Thumbprint)" -Force
        
    } catch {
        Write-Host "ERROR: Failed to create self-signed certificate: $_" -ForegroundColor Red
        Write-Host "Please create TLS certificates manually and place them at:" -ForegroundColor Yellow
        Write-Host "  Certificate: $certPath" -ForegroundColor White
        Write-Host "  Private Key: $keyPath" -ForegroundColor White
        exit 1
    }
} else {
    Write-Host "  [OK] TLS certificates found" -ForegroundColor Green
}

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host ""
    Write-Host "WARNING: Service '$ServiceName' already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to reinstall? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Installation cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    # Stop and remove existing service
    if ($existingService.Status -eq "Running") {
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
    }
    nssm remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Install service
Write-Host ""
Write-Host "Installing Caddy service..." -ForegroundColor Cyan

# Set environment variables for Caddy
$env:DOMAIN = $domain
$env:TLS_CERT_PATH = $certPath
$env:TLS_KEY_PATH = $keyPath

# Install service with NSSM
nssm install $ServiceName $caddyExePath
nssm set $ServiceName AppDirectory $InstallPath
nssm set $ServiceName AppParameters "run --config `"$caddyfile`" --adapter caddyfile"
nssm set $ServiceName DisplayName "Caddy Reverse Proxy (Mailroom)"
nssm set $ServiceName Description "HTTPS reverse proxy for Mailroom Tracking System"
nssm set $ServiceName Start SERVICE_AUTO_START

# Set environment variables
nssm set $ServiceName AppEnvironmentExtra "DOMAIN=$domain" "TLS_CERT_PATH=$certPath" "TLS_KEY_PATH=$keyPath"

# Set up logging
$stdoutLog = Join-Path $InstallPath "logs\caddy-stdout.log"
$stderrLog = Join-Path $InstallPath "logs\caddy-stderr.log"
nssm set $ServiceName AppStdout $stdoutLog
nssm set $ServiceName AppStderr $stderrLog
nssm set $ServiceName AppStdoutCreationDisposition 4
nssm set $ServiceName AppStderrCreationDisposition 4

# Set restart policy
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 5000

Write-Host "  [OK] Service installed" -ForegroundColor Green

# Start service
Write-Host ""
$response = Read-Host "Do you want to start the Caddy service now? (Y/n)"
if ($response -ne "n" -and $response -ne "N") {
    Write-Host "Starting service..." -ForegroundColor Yellow
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Host "  [OK] Service started successfully" -ForegroundColor Green
    } else {
        Write-Host "  [!] Service failed to start" -ForegroundColor Red
        Write-Host "Check logs at: $stderrLog" -ForegroundColor Yellow
    }
}

# Display summary
Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Service Name: $ServiceName"
Write-Host "Domain: $domain"
Write-Host "HTTPS URL: https://$domain"
Write-Host ""
Write-Host "Service Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Stop:    Stop-Service $ServiceName"
Write-Host "  Restart: Restart-Service $ServiceName"
Write-Host "  Status:  Get-Service $ServiceName"
Write-Host ""
Write-Host "Logs:" -ForegroundColor Cyan
Write-Host "  Access:  $InstallPath\logs\caddy-access.log"
Write-Host "  Error:   $InstallPath\logs\caddy-error.log"
Write-Host "  Stdout:  $stdoutLog"
Write-Host "  Stderr:  $stderrLog"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Ensure Mailroom service is running"
Write-Host "  2. Add DNS entry for $domain pointing to this server"
Write-Host "  3. Configure firewall to allow HTTPS (port 443)"
Write-Host "  4. Test access: https://$domain"
Write-Host ""

if (Test-Path $certPath) {
    $certContent = Get-Content $certPath -Raw
    if ($certContent -match "BEGIN CERTIFICATE") {
        Write-Host "NOTE: Using self-signed certificate" -ForegroundColor Yellow
        Write-Host "For production, replace with certificates from your internal CA" -ForegroundColor Yellow
        Write-Host ""
    }
}
