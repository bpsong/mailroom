# Mailroom Tracking System - Backup Script
# This script creates daily backups of the database and uploaded files

param(
    [string]$InstallPath = "C:\MailroomApp",
    [string]$BackupPath = "C:\Backups\Mailroom",
    [switch]$SkipCompression,
    [switch]$Help
)

# Display help
if ($Help) {
    Write-Host @"
Mailroom Tracking System - Backup Script

Usage:
    .\backup.ps1 [options]

Options:
    -InstallPath <path>     Installation directory (default: C:\MailroomApp)
    -BackupPath <path>      Backup destination directory (default: C:\Backups\Mailroom)
    -SkipCompression        Skip ZIP compression (faster but uses more space)
    -Help                   Display this help message

Examples:
    # Create backup with defaults
    .\backup.ps1

    # Create backup to custom location
    .\backup.ps1 -BackupPath "D:\Backups\Mailroom"

    # Create uncompressed backup (faster)
    .\backup.ps1 -SkipCompression

Scheduled Task Setup:
    # Run daily at 2 AM
    `$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\MailroomApp\scripts\backup.ps1"
    `$trigger = New-ScheduledTaskTrigger -Daily -At 2am
    Register-ScheduledTask -TaskName "MailroomBackup" -Action `$action -Trigger `$trigger -User "SYSTEM"

"@
    exit 0
}

Write-Host "Mailroom Tracking System - Backup" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Validate installation directory
if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Installation directory not found: $InstallPath" -ForegroundColor Red
    exit 1
}

Write-Host "`nInstallation: $InstallPath" -ForegroundColor Green

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupPath)) {
    Write-Host "Creating backup directory: $BackupPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
}

Write-Host "Backup destination: $BackupPath" -ForegroundColor Green

# Generate timestamp for backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "mailroom_backup_$timestamp"
$backupDir = Join-Path $BackupPath $backupName

Write-Host "`nBackup name: $backupName" -ForegroundColor Cyan

# Create temporary backup directory
Write-Host "`nCreating backup directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup database
$dbPath = Join-Path $InstallPath "data\mailroom.duckdb"
if (Test-Path $dbPath) {
    Write-Host "Backing up database..." -ForegroundColor Yellow
    
    $dbBackupPath = Join-Path $backupDir "data"
    New-Item -ItemType Directory -Path $dbBackupPath -Force | Out-Null
    
    try {
        # Copy main database file
        Copy-Item $dbPath $dbBackupPath -Force
        
        # Copy WAL file if it exists
        $walPath = "$dbPath.wal"
        if (Test-Path $walPath) {
            Copy-Item $walPath $dbBackupPath -Force
        }
        
        $dbSize = (Get-Item $dbPath).Length
        Write-Host "  Database backed up: $([math]::Round($dbSize/1MB, 2)) MB" -ForegroundColor Green
    }
    catch {
        Write-Host "  ERROR: Failed to backup database: $_" -ForegroundColor Red
        Remove-Item -Recurse -Force $backupDir -ErrorAction SilentlyContinue
        exit 1
    }
}
else {
    Write-Host "WARNING: Database not found at: $dbPath" -ForegroundColor Yellow
}

# Backup uploaded files
$uploadDir = Join-Path $InstallPath "uploads"
if (Test-Path $uploadDir) {
    Write-Host "Backing up uploaded files..." -ForegroundColor Yellow
    
    try {
        Copy-Item -Recurse $uploadDir $backupDir -Force
        
        $fileCount = (Get-ChildItem -Recurse $uploadDir -File).Count
        $uploadSize = (Get-ChildItem -Recurse $uploadDir -File | Measure-Object -Property Length -Sum).Sum
        
        if ($uploadSize) {
            Write-Host "  Uploaded files backed up: $fileCount files, $([math]::Round($uploadSize/1MB, 2)) MB" -ForegroundColor Green
        }
        else {
            Write-Host "  Uploaded files backed up: $fileCount files" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  ERROR: Failed to backup uploads: $_" -ForegroundColor Red
        Remove-Item -Recurse -Force $backupDir -ErrorAction SilentlyContinue
        exit 1
    }
}
else {
    Write-Host "WARNING: Upload directory not found at: $uploadDir" -ForegroundColor Yellow
}

# Backup .env file (contains configuration)
$envPath = Join-Path $InstallPath ".env"
if (Test-Path $envPath) {
    Write-Host "Backing up configuration..." -ForegroundColor Yellow
    
    try {
        Copy-Item $envPath $backupDir -Force
        Write-Host "  Configuration backed up" -ForegroundColor Green
    }
    catch {
        Write-Host "  WARNING: Failed to backup .env file: $_" -ForegroundColor Yellow
    }
}

# Create backup manifest
$manifestPath = Join-Path $backupDir "backup_manifest.txt"
$manifest = @"
Mailroom Tracking System Backup
================================

Backup Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Backup Name: $backupName
Installation Path: $InstallPath

Contents:
---------
"@

if (Test-Path (Join-Path $backupDir "data\mailroom.duckdb")) {
    $dbSize = (Get-Item (Join-Path $backupDir "data\mailroom.duckdb")).Length
    $manifest += "`n- Database: mailroom.duckdb ($([math]::Round($dbSize/1MB, 2)) MB)"
}

if (Test-Path (Join-Path $backupDir "uploads")) {
    $fileCount = (Get-ChildItem -Recurse (Join-Path $backupDir "uploads") -File).Count
    $uploadSize = (Get-ChildItem -Recurse (Join-Path $backupDir "uploads") -File | Measure-Object -Property Length -Sum).Sum
    if ($uploadSize) {
        $manifest += "`n- Uploads: $fileCount files ($([math]::Round($uploadSize/1MB, 2)) MB)"
    }
    else {
        $manifest += "`n- Uploads: $fileCount files"
    }
}

if (Test-Path (Join-Path $backupDir ".env")) {
    $manifest += "`n- Configuration: .env"
}

$manifest | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Host "`nBackup manifest created" -ForegroundColor Green

# Compress backup
if (-not $SkipCompression) {
    Write-Host "`nCompressing backup..." -ForegroundColor Yellow
    
    $zipPath = "$backupDir.zip"
    
    try {
        Compress-Archive -Path $backupDir -DestinationPath $zipPath -CompressionLevel Optimal -Force
        
        $zipSize = (Get-Item $zipPath).Length
        Write-Host "  Backup compressed: $([math]::Round($zipSize/1MB, 2)) MB" -ForegroundColor Green
        
        # Remove uncompressed directory
        Remove-Item -Recurse -Force $backupDir
        
        $finalBackupPath = $zipPath
    }
    catch {
        Write-Host "  ERROR: Failed to compress backup: $_" -ForegroundColor Red
        Write-Host "  Keeping uncompressed backup" -ForegroundColor Yellow
        $finalBackupPath = $backupDir
    }
}
else {
    Write-Host "`nSkipping compression (as requested)" -ForegroundColor Yellow
    $finalBackupPath = $backupDir
}

# Calculate total backup size
if (Test-Path $finalBackupPath) {
    if ($finalBackupPath -like "*.zip") {
        $totalSize = (Get-Item $finalBackupPath).Length
    }
    else {
        $totalSize = (Get-ChildItem -Recurse $finalBackupPath -File | Measure-Object -Property Length -Sum).Sum
    }
    
    Write-Host "`nBackup completed successfully!" -ForegroundColor Green
    Write-Host "Location: $finalBackupPath" -ForegroundColor Cyan
    Write-Host "Total size: $([math]::Round($totalSize/1MB, 2)) MB" -ForegroundColor Cyan
    
    # Show disk space
    $drive = Split-Path -Qualifier $BackupPath
    $driveInfo = Get-PSDrive -Name $drive.TrimEnd(':')
    $freeSpace = $driveInfo.Free
    Write-Host "Free space on $drive`: $([math]::Round($freeSpace/1GB, 2)) GB" -ForegroundColor White
    
    # Warn if low disk space
    if ($freeSpace -lt 1GB) {
        Write-Host "`nWARNING: Low disk space on backup drive!" -ForegroundColor Red
        Write-Host "Consider running cleanup script or freeing up space" -ForegroundColor Yellow
    }
}
else {
    Write-Host "`nERROR: Backup failed - backup directory not found" -ForegroundColor Red
    exit 1
}

Write-Host "`nBackup process complete!" -ForegroundColor Green
Write-Host "`nRecommendations:" -ForegroundColor Cyan
Write-Host "  - Test backup restoration periodically" -ForegroundColor White
Write-Host "  - Run cleanup script to remove old backups (30-day retention)" -ForegroundColor White
Write-Host "  - Monitor backup drive disk space" -ForegroundColor White
Write-Host "  - Consider offsite backup storage for disaster recovery" -ForegroundColor White

