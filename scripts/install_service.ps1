# Mailroom Tracking System - Windows Service Installation Script
# This script installs the application as a Windows Service using NSSM

param(
    [string]$InstallPath = "C:\MailroomApp",
    [string]$ServiceName = "MailroomTracking",
    [string]$PythonPath = "C:\Python312\python.exe",
    [switch]$Uninstall,
    [switch]$Help
)

# Display help
if ($Help) {
    Write-Host @"
Mailroom Tracking System - Service Installation Script

Usage:
    .\install_service.ps1 [options]

Options:
    -InstallPath <path>    Installation directory (default: C:\MailroomApp)
    -ServiceName <name>    Service name (default: MailroomTracking)
    -PythonPath <path>     Path to Python executable (default: C:\Python312\python.exe)
    -Uninstall            Uninstall the service
    -Help                 Display this help message

Examples:
    # Install service with defaults
    .\install_service.ps1

    # Install service with custom path
    .\install_service.ps1 -InstallPath "D:\Apps\Mailroom"

    # Uninstall service
    .\install_service.ps1 -Uninstall

Requirements:
    - NSSM (Non-Sucking Service Manager) must be installed
    - Run as Administrator
    - Python 3.12+ must be installed
"@
    exit 0
}

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if NSSM is installed
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    Write-Host "ERROR: NSSM is not installed" -ForegroundColor Red
    Write-Host "Install NSSM using one of these methods:" -ForegroundColor Yellow
    Write-Host "  1. Chocolatey: choco install nssm" -ForegroundColor Cyan
    Write-Host "  2. Download from: https://nssm.cc/download" -ForegroundColor Cyan
    exit 1
}

Write-Host "NSSM found at: $($nssmPath.Source)" -ForegroundColor Green

# Uninstall service if requested
if ($Uninstall) {
    Write-Host "`nUninstalling service: $ServiceName" -ForegroundColor Yellow
    
    # Check if service exists
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Host "Service '$ServiceName' is not installed" -ForegroundColor Yellow
        exit 0
    }
    
    # Stop service if running
    if ($service.Status -eq 'Running') {
        Write-Host "Stopping service..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
    }
    
    # Remove service
    Write-Host "Removing service..." -ForegroundColor Yellow
    & nssm remove $ServiceName confirm
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Service uninstalled successfully" -ForegroundColor Green
    } else {
        Write-Host "Failed to uninstall service" -ForegroundColor Red
        exit 1
    }
    
    exit 0
}

# Validate Python installation
if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at: $PythonPath" -ForegroundColor Red
    Write-Host "Please install Python 3.12+ or specify correct path with -PythonPath" -ForegroundColor Yellow
    exit 1
}

# Check Python version
$pythonVersion = & $PythonPath --version 2>&1
Write-Host "Python found: $pythonVersion" -ForegroundColor Green

# Validate installation directory
if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Installation directory not found: $InstallPath" -ForegroundColor Red
    Write-Host "Please ensure the application is deployed to this directory" -ForegroundColor Yellow
    exit 1
}

# Check if main.py exists
$mainPyPath = Join-Path $InstallPath "app\main.py"
if (-not (Test-Path $mainPyPath)) {
    Write-Host "ERROR: Application not found at: $mainPyPath" -ForegroundColor Red
    exit 1
}

Write-Host "Application found at: $InstallPath" -ForegroundColor Green

# Check if .env file exists
$envPath = Join-Path $InstallPath ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "WARNING: .env file not found at: $envPath" -ForegroundColor Yellow
    Write-Host "Please create .env file before starting the service" -ForegroundColor Yellow
}

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "`nWARNING: Service '$ServiceName' already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to reinstall? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Installation cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    # Stop and remove existing service
    Write-Host "Stopping existing service..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    & nssm remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Install service
Write-Host "`nInstalling service: $ServiceName" -ForegroundColor Cyan
Write-Host "Installation path: $InstallPath" -ForegroundColor Cyan
Write-Host "Python path: $PythonPath" -ForegroundColor Cyan

# Create service
Write-Host "`nCreating service..." -ForegroundColor Yellow
& nssm install $ServiceName $PythonPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create service" -ForegroundColor Red
    exit 1
}

# Configure service
Write-Host "Configuring service..." -ForegroundColor Yellow

# Set application directory
& nssm set $ServiceName AppDirectory $InstallPath

# Set application parameters (run uvicorn)
$appParams = "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
& nssm set $ServiceName AppParameters $appParams

# Set display name and description
& nssm set $ServiceName DisplayName "Mailroom Tracking System"
& nssm set $ServiceName Description "Internal package tracking application for mailroom operations"

# Set startup type to automatic
& nssm set $ServiceName Start SERVICE_AUTO_START

# Set service to restart on failure
& nssm set $ServiceName AppExit Default Restart
& nssm set $ServiceName AppRestartDelay 5000

# Set stdout and stderr logging
$logDir = Join-Path $InstallPath "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$stdoutLog = Join-Path $logDir "service-stdout.log"
$stderrLog = Join-Path $logDir "service-stderr.log"

& nssm set $ServiceName AppStdout $stdoutLog
& nssm set $ServiceName AppStderr $stderrLog

# Rotate logs
& nssm set $ServiceName AppStdoutCreationDisposition 4
& nssm set $ServiceName AppStderrCreationDisposition 4

# Set environment variable for production
& nssm set $ServiceName AppEnvironmentExtra "APP_ENV=production"

Write-Host "`nService installed successfully!" -ForegroundColor Green
Write-Host "`nService Details:" -ForegroundColor Cyan
Write-Host "  Name: $ServiceName" -ForegroundColor White
Write-Host "  Display Name: Mailroom Tracking System" -ForegroundColor White
Write-Host "  Installation Path: $InstallPath" -ForegroundColor White
Write-Host "  Python: $PythonPath" -ForegroundColor White
Write-Host "  Startup Type: Automatic" -ForegroundColor White
Write-Host "  Stdout Log: $stdoutLog" -ForegroundColor White
Write-Host "  Stderr Log: $stderrLog" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Ensure .env file is configured at: $envPath" -ForegroundColor White
Write-Host "  2. Start the service: Start-Service $ServiceName" -ForegroundColor White
Write-Host "  3. Check service status: Get-Service $ServiceName" -ForegroundColor White
Write-Host "  4. View logs in: $logDir" -ForegroundColor White

Write-Host "`nService Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service $ServiceName" -ForegroundColor White
Write-Host "  Stop:    Stop-Service $ServiceName" -ForegroundColor White
Write-Host "  Restart: Restart-Service $ServiceName" -ForegroundColor White
Write-Host "  Status:  Get-Service $ServiceName" -ForegroundColor White
Write-Host "  Logs:    Get-Content '$stdoutLog' -Tail 50" -ForegroundColor White

# Ask if user wants to start the service now
Write-Host ""
$startNow = Read-Host "Do you want to start the service now? (y/N)"
if ($startNow -eq 'y' -or $startNow -eq 'Y') {
    Write-Host "`nStarting service..." -ForegroundColor Yellow
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq 'Running') {
        Write-Host "Service started successfully!" -ForegroundColor Green
        Write-Host "Application should be accessible at: http://localhost:8000" -ForegroundColor Cyan
    } else {
        Write-Host "Service failed to start. Check logs for details:" -ForegroundColor Red
        Write-Host "  $stderrLog" -ForegroundColor Yellow
    }
}

Write-Host "`nInstallation complete!" -ForegroundColor Green
