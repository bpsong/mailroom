# Mailroom Tracking System - SQLite Database Administration Script
# Wrapper around scripts/migrate.py for common database setup/maintenance operations.

param(
    [ValidateSet('init', 'bootstrap', 'verify', 'reset')]
    [string]$Command = 'init',
    [string]$InstallPath = 'C:\MailroomApp',
    [string]$PythonPath = 'C:\Python313\python.exe',
    [string]$Username = 'admin',
    [string]$Password = 'ChangeMe123!',
    [string]$FullName = 'System Administrator',
    [switch]$NoSuperAdmin,
    [switch]$ConfirmReset,
    [switch]$VerboseOutput,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Mailroom Tracking System - SQLite Database Administration Script

Usage:
    .\database_admin.ps1 [options]

Options:
    -Command <init|bootstrap|verify|reset>  Action to run (default: init)
    -InstallPath <path>                     Installation directory (default: C:\MailroomApp)
    -PythonPath <path>                      Path to Python executable (default: C:\Python313\python.exe)
    -Username <name>                        Admin username for init/bootstrap (default: admin)
    -Password <pass>                        Admin password for init/bootstrap (default: ChangeMe123!)
    -FullName <name>                        Admin full name for init/bootstrap (default: System Administrator)
    -NoSuperAdmin                           For init only: skip creating the super admin account
    -ConfirmReset                           Required when Command=reset
    -VerboseOutput                          Enable verbose migration logging
    -Help                                   Display this help message

Examples:
    # Initialize schema and create super admin
    .\database_admin.ps1 -Command init -Username superadmin -FullName "John Doe"

    # Verify SQLite schema
    .\database_admin.ps1 -Command verify

    # Reset database (WARNING: deletes all data)
    .\database_admin.ps1 -Command reset -ConfirmReset
"@
    exit 0
}

Write-Host "Mailroom Tracking System - SQLite Database Administration" -ForegroundColor Cyan
Write-Host ('=' * 64) -ForegroundColor Cyan

if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at: $PythonPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Installation directory not found: $InstallPath" -ForegroundColor Red
    exit 1
}

$migrateScript = Join-Path $InstallPath 'scripts\migrate.py'
if (-not (Test-Path $migrateScript)) {
    Write-Host "ERROR: Migration CLI not found at: $migrateScript" -ForegroundColor Red
    exit 1
}

$commonArgs = @()
if ($VerboseOutput) {
    $commonArgs += '--verbose'
}

Push-Location $InstallPath
try {
    switch ($Command) {
        'init' {
            $cmdArgs = @($migrateScript, 'init')
            if ($NoSuperAdmin) {
                $cmdArgs += '--no-super-admin'
            } else {
                $cmdArgs += @('--username', $Username, '--password', $Password, '--full-name', $FullName)
            }
            $cmdArgs += $commonArgs
            & $PythonPath @cmdArgs
            exit $LASTEXITCODE
        }

        'bootstrap' {
            $cmdArgs = @(
                $migrateScript,
                'bootstrap',
                '--username', $Username,
                '--password', $Password,
                '--full-name', $FullName
            )
            $cmdArgs += $commonArgs
            & $PythonPath @cmdArgs
            exit $LASTEXITCODE
        }

        'verify' {
            $cmdArgs = @($migrateScript, 'verify')
            $cmdArgs += $commonArgs
            & $PythonPath @cmdArgs
            exit $LASTEXITCODE
        }

        'reset' {
            if (-not $ConfirmReset) {
                Write-Host 'ERROR: -ConfirmReset is required when Command=reset.' -ForegroundColor Red
                exit 1
            }

            Write-Host 'WARNING: This will delete all database data.' -ForegroundColor Yellow
            Write-Host "Running reset against install path: $InstallPath" -ForegroundColor Yellow

            $cmdArgs = @($migrateScript, 'reset', '--confirm')
            $cmdArgs += $commonArgs

            # migrate.py prompts for an additional interactive confirmation.
            'yes' | & $PythonPath @cmdArgs
            exit $LASTEXITCODE
        }
    }
} finally {
    Pop-Location
}
