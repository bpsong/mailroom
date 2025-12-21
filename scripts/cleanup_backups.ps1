# Mailroom Tracking System - Backup Cleanup Script
# This script removes backups older than the specified retention period

param(
    [string]$BackupPath = "C:\Backups\Mailroom",
    [int]$RetentionDays = 30,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Help
)

# Display help
if ($Help) {
    Write-Host @"
Mailroom Tracking System - Backup Cleanup Script

Usage:
    .\cleanup_backups.ps1 [options]

Options:
    -BackupPath <path>      Backup directory to clean (default: C:\Backups\Mailroom)
    -RetentionDays <days>   Number of days to retain backups (default: 30)
    -DryRun                 Show what would be deleted without actually deleting
    -Force                  Skip confirmation prompt
    -Help                   Display this help message

Examples:
    # Preview cleanup (dry run)
    .\cleanup_backups.ps1 -DryRun

    # Clean backups older than 30 days (default)
    .\cleanup_backups.ps1

    # Clean backups older than 90 days
    .\cleanup_backups.ps1 -RetentionDays 90

    # Clean without confirmation
    .\cleanup_backups.ps1 -Force

Scheduled Task Setup:
    # Run weekly on Sunday at 3 AM
    `$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\MailroomApp\scripts\cleanup_backups.ps1 -Force"
    `$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
    Register-ScheduledTask -TaskName "MailroomBackupCleanup" -Action `$action -Trigger `$trigger -User "SYSTEM"

"@
    exit 0
}

Write-Host "Mailroom Tracking System - Backup Cleanup" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Validate backup directory
if (-not (Test-Path $BackupPath)) {
    Write-Host "ERROR: Backup directory not found: $BackupPath" -ForegroundColor Red
    exit 1
}

Write-Host "`nBackup directory: $BackupPath" -ForegroundColor Green
Write-Host "Retention period: $RetentionDays days" -ForegroundColor Green

if ($DryRun) {
    Write-Host "Mode: DRY RUN (no files will be deleted)" -ForegroundColor Yellow
}

# Calculate cutoff date
$cutoffDate = (Get-Date).AddDays(-$RetentionDays)
Write-Host "Cutoff date: $($cutoffDate.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host "Backups older than this date will be removed" -ForegroundColor White

# Find old backups
Write-Host "`nScanning for old backups..." -ForegroundColor Yellow

# Find both compressed (.zip) and uncompressed (directories) backups
$oldZipBackups = Get-ChildItem -Path $BackupPath -Filter "mailroom_backup_*.zip" -File | 
    Where-Object { $_.CreationTime -lt $cutoffDate }

$oldDirBackups = Get-ChildItem -Path $BackupPath -Filter "mailroom_backup_*" -Directory | 
    Where-Object { $_.CreationTime -lt $cutoffDate }

$oldBackups = @($oldZipBackups) + @($oldDirBackups)

if ($oldBackups.Count -eq 0) {
    Write-Host "`nNo old backups found" -ForegroundColor Green
    Write-Host "All backups are within the $RetentionDays-day retention period" -ForegroundColor White
    exit 0
}

# Display old backups
Write-Host "`nFound $($oldBackups.Count) old backup(s):" -ForegroundColor Yellow
Write-Host ""

$totalSize = 0
foreach ($backup in $oldBackups) {
    $age = [math]::Round(((Get-Date) - $backup.CreationTime).TotalDays, 1)
    
    if ($backup.PSIsContainer) {
        # Directory backup
        $size = (Get-ChildItem -Recurse $backup.FullName -File | Measure-Object -Property Length -Sum).Sum
    }
    else {
        # ZIP backup
        $size = $backup.Length
    }
    
    $totalSize += $size
    $sizeStr = "$([math]::Round($size/1MB, 2)) MB"
    
    Write-Host "  $($backup.Name)" -ForegroundColor White
    Write-Host "    Created: $($backup.CreationTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
    Write-Host "    Age: $age days" -ForegroundColor Gray
    Write-Host "    Size: $sizeStr" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Total size to be freed: $([math]::Round($totalSize/1MB, 2)) MB" -ForegroundColor Cyan

# Dry run mode - exit without deleting
if ($DryRun) {
    Write-Host "`nDRY RUN: No files were deleted" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to actually delete these backups" -ForegroundColor White
    exit 0
}

# Confirmation prompt (unless -Force is used)
if (-not $Force) {
    Write-Host "`nWARNING: This will permanently delete $($oldBackups.Count) backup(s)" -ForegroundColor Yellow
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
    
    if ($confirmation -ne 'yes') {
        Write-Host "Cleanup cancelled" -ForegroundColor Yellow
        exit 0
    }
}

# Delete old backups
Write-Host "`nDeleting old backups..." -ForegroundColor Yellow

$deletedCount = 0
$failedCount = 0
$freedSpace = 0

foreach ($backup in $oldBackups) {
    try {
        if ($backup.PSIsContainer) {
            $size = (Get-ChildItem -Recurse $backup.FullName -File | Measure-Object -Property Length -Sum).Sum
            Remove-Item -Recurse -Force $backup.FullName
        }
        else {
            $size = $backup.Length
            Remove-Item -Force $backup.FullName
        }
        
        Write-Host "  Deleted: $($backup.Name)" -ForegroundColor Green
        $deletedCount++
        $freedSpace += $size
    }
    catch {
        Write-Host "  ERROR: Failed to delete $($backup.Name): $_" -ForegroundColor Red
        $failedCount++
    }
}

# Summary
Write-Host "`nCleanup Summary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deletedCount backup(s)" -ForegroundColor Green
Write-Host "  Failed: $failedCount backup(s)" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "White" })
Write-Host "  Space freed: $([math]::Round($freedSpace/1MB, 2)) MB" -ForegroundColor Cyan

# Show remaining backups
$remainingBackups = @(Get-ChildItem -Path $BackupPath -Filter "mailroom_backup_*.zip" -File) + 
                    @(Get-ChildItem -Path $BackupPath -Filter "mailroom_backup_*" -Directory)

if ($remainingBackups.Count -gt 0) {
    Write-Host "`nRemaining backups: $($remainingBackups.Count)" -ForegroundColor White
    
    # Show oldest and newest
    $oldest = $remainingBackups | Sort-Object CreationTime | Select-Object -First 1
    $newest = $remainingBackups | Sort-Object CreationTime -Descending | Select-Object -First 1
    
    Write-Host "  Oldest: $($oldest.Name) ($($oldest.CreationTime.ToString('yyyy-MM-dd')))" -ForegroundColor Gray
    Write-Host "  Newest: $($newest.Name) ($($newest.CreationTime.ToString('yyyy-MM-dd')))" -ForegroundColor Gray
}
else {
    Write-Host "`nNo backups remaining" -ForegroundColor Yellow
}

# Show disk space
$drive = Split-Path -Qualifier $BackupPath
$driveInfo = Get-PSDrive -Name $drive.TrimEnd(':')
$freeSpace = $driveInfo.Free
Write-Host "`nFree space on $drive`: $([math]::Round($freeSpace/1GB, 2)) GB" -ForegroundColor White

Write-Host "`nCleanup complete!" -ForegroundColor Green

if ($failedCount -gt 0) {
    Write-Host "`nWARNING: Some backups could not be deleted" -ForegroundColor Yellow
    Write-Host "Check file permissions and try again" -ForegroundColor White
    exit 1
}

exit 0
