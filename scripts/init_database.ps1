# Mailroom Tracking System - Database Initialization Script
# This script initializes the database and creates the super admin user

param(
    [string]$InstallPath = "C:\MailroomApp",
    [string]$PythonPath = "C:\Python312\python.exe",
    [string]$SuperAdminUsername = "admin",
    [string]$SuperAdminPassword,
    [string]$SuperAdminFullName = "System Administrator",
    [switch]$ResetDatabase,
    [switch]$Help
)

# Display help
if ($Help) {
    Write-Host @"
Mailroom Tracking System - Database Initialization Script

Usage:
    .\init_database.ps1 [options]

Options:
    -InstallPath <path>           Installation directory (default: C:\MailroomApp)
    -PythonPath <path>            Path to Python executable (default: C:\Python312\python.exe)
    -SuperAdminUsername <name>    Super admin username (default: admin)
    -SuperAdminPassword <pass>    Super admin password (will prompt if not provided)
    -SuperAdminFullName <name>    Super admin full name (default: System Administrator)
    -ResetDatabase                Delete existing database and recreate
    -Help                         Display this help message

Examples:
    # Initialize database with defaults (will prompt for password)
    .\init_database.ps1

    # Initialize with custom super admin
    .\init_database.ps1 -SuperAdminUsername "superadmin" -SuperAdminFullName "John Doe"

    # Reset database (WARNING: deletes all data)
    .\init_database.ps1 -ResetDatabase

Requirements:
    - Python 3.12+ must be installed
    - Application must be deployed to InstallPath
    - .env file must be configured
"@
    exit 0
}

Write-Host "Mailroom Tracking System - Database Initialization" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Validate Python installation
if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at: $PythonPath" -ForegroundColor Red
    Write-Host "Please install Python 3.12+ or specify correct path with -PythonPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nPython: $PythonPath" -ForegroundColor Green

# Validate installation directory
if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Installation directory not found: $InstallPath" -ForegroundColor Red
    exit 1
}

Write-Host "Installation: $InstallPath" -ForegroundColor Green

# Check if .env file exists
$envPath = Join-Path $InstallPath ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "ERROR: .env file not found at: $envPath" -ForegroundColor Red
    Write-Host "Please create .env file before initializing database" -ForegroundColor Yellow
    exit 1
}

Write-Host "Configuration: $envPath" -ForegroundColor Green

# Determine database path from .env
$dbPath = Join-Path $InstallPath "data\mailroom.duckdb"
$envContent = Get-Content $envPath
foreach ($line in $envContent) {
    if ($line -match '^DATABASE_PATH=(.+)$') {
        $dbPath = $matches[1].Trim()
        # Convert relative path to absolute
        if (-not [System.IO.Path]::IsPathRooted($dbPath)) {
            $dbPath = Join-Path $InstallPath $dbPath
        }
        break
    }
}

Write-Host "Database: $dbPath" -ForegroundColor Green

# Check if database already exists
$dbExists = Test-Path $dbPath

if ($dbExists) {
    if ($ResetDatabase) {
        Write-Host "`nWARNING: Database reset requested" -ForegroundColor Yellow
        Write-Host "This will DELETE ALL DATA in the database!" -ForegroundColor Red
        $confirm = Read-Host "Are you sure you want to continue? Type 'DELETE' to confirm"
        
        if ($confirm -ne 'DELETE') {
            Write-Host "Database reset cancelled" -ForegroundColor Yellow
            exit 0
        }
        
        Write-Host "`nDeleting existing database..." -ForegroundColor Yellow
        Remove-Item $dbPath -Force
        
        # Also remove WAL files if they exist
        $walPath = "$dbPath.wal"
        if (Test-Path $walPath) {
            Remove-Item $walPath -Force
        }
        
        Write-Host "Database deleted" -ForegroundColor Green
        $dbExists = $false
    } else {
        Write-Host "`nDatabase already exists" -ForegroundColor Yellow
        Write-Host "Use -ResetDatabase to delete and recreate (WARNING: deletes all data)" -ForegroundColor Yellow
        
        $response = Read-Host "Do you want to continue with existing database? (y/N)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "Initialization cancelled" -ForegroundColor Yellow
            exit 0
        }
    }
}

# Prompt for super admin password if not provided
if (-not $SuperAdminPassword) {
    Write-Host "`nSuper Admin Account Setup" -ForegroundColor Cyan
    Write-Host "Username: $SuperAdminUsername" -ForegroundColor White
    Write-Host "Full Name: $SuperAdminFullName" -ForegroundColor White
    Write-Host ""
    
    $securePassword = Read-Host "Enter super admin password (min 12 chars)" -AsSecureString
    $confirmPassword = Read-Host "Confirm password" -AsSecureString
    
    # Convert secure strings to plain text for comparison
    $BSTR1 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $BSTR2 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($confirmPassword)
    $password1 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR1)
    $password2 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR2)
    
    if ($password1 -ne $password2) {
        Write-Host "ERROR: Passwords do not match" -ForegroundColor Red
        exit 1
    }
    
    if ($password1.Length -lt 12) {
        Write-Host "ERROR: Password must be at least 12 characters" -ForegroundColor Red
        exit 1
    }
    
    $SuperAdminPassword = $password1
    
    # Clear sensitive data
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR1)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR2)
}

# Create Python script to initialize database
$initScript = @"
import sys
import os

# Add application directory to path
sys.path.insert(0, r'$InstallPath')

# Set environment variable to load .env
os.environ['DOTENV_PATH'] = r'$envPath'

from app.database.migrations import run_initial_migration

# Run migration with super admin creation
try:
    run_initial_migration(
        create_super_admin=True,
        super_admin_username='$SuperAdminUsername',
        super_admin_password='$SuperAdminPassword',
        super_admin_full_name='$SuperAdminFullName'
    )
    print('SUCCESS: Database initialized successfully')
except Exception as e:
    print(f'ERROR: {str(e)}')
    sys.exit(1)
"@

$tempScript = Join-Path $env:TEMP "init_db_temp.py"
$initScript | Out-File -FilePath $tempScript -Encoding UTF8

# Run initialization
Write-Host "`nInitializing database..." -ForegroundColor Yellow

try {
    $output = & $PythonPath $tempScript 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nDatabase initialized successfully!" -ForegroundColor Green
        Write-Host "`nSuper Admin Account:" -ForegroundColor Cyan
        Write-Host "  Username: $SuperAdminUsername" -ForegroundColor White
        Write-Host "  Full Name: $SuperAdminFullName" -ForegroundColor White
        Write-Host "  Role: super_admin" -ForegroundColor White
        Write-Host "`nIMPORTANT: Save these credentials securely!" -ForegroundColor Yellow
        
        # Check database file was created
        if (Test-Path $dbPath) {
            $dbSize = (Get-Item $dbPath).Length
            Write-Host "`nDatabase file created: $dbPath" -ForegroundColor Green
            Write-Host "Database size: $([math]::Round($dbSize/1KB, 2)) KB" -ForegroundColor White
        }
        
        Write-Host "`nNext Steps:" -ForegroundColor Cyan
        Write-Host "  1. Start the application or service" -ForegroundColor White
        Write-Host "  2. Navigate to the application URL" -ForegroundColor White
        Write-Host "  3. Log in with super admin credentials" -ForegroundColor White
        Write-Host "  4. Create additional admin and operator accounts" -ForegroundColor White
        Write-Host "  5. Change the super admin password" -ForegroundColor White
        
    } else {
        Write-Host "`nERROR: Database initialization failed" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
        exit 1
    }
} finally {
    # Clean up temp script
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force
    }
}

Write-Host "`nInitialization complete!" -ForegroundColor Green
