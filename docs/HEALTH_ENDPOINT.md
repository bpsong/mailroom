# Health Check Endpoint Documentation

## Overview

The health check endpoint provides comprehensive monitoring of the Mailroom Tracking System's operational status. It can be used by monitoring tools, load balancers, or administrators to verify system health.

## Endpoint

```
GET /health
```

**Authentication:** Not required (public endpoint for monitoring)

## Response Format

The endpoint returns a JSON object with the following structure:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-12T13:51:31.256574",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful",
      "connected": true
    },
    "disk_space": {
      "status": "healthy",
      "database_directory": {
        "path": "data",
        "total_gb": 931.41,
        "used_gb": 204.32,
        "free_gb": 727.1,
        "percent_used": 21.94
      },
      "upload_directory": {
        "path": "uploads",
        "total_gb": 931.41,
        "used_gb": 204.32,
        "free_gb": 727.1,
        "percent_used": 21.94
      }
    },
    "uptime": {
      "status": "healthy",
      "started_at": "2025-11-12T21:51:31.236603",
      "uptime_seconds": 0,
      "uptime_formatted": "0d 0h 0m 0s"
    }
  }
}
```

## Status Values

### Overall Status
- `healthy`: All systems operational
- `unhealthy`: One or more critical systems are down

### Component Status
- `healthy`: Component is functioning normally
- `warning`: Component is functional but approaching limits (e.g., disk space > 90%)
- `unhealthy`: Component has failed
- `error`: Unable to check component status

## Health Checks

### 1. Database Connection
Verifies that the application can connect to and query the DuckDB database.

**Healthy Criteria:**
- Database connection successful
- Can execute test query

**Response Fields:**
- `status`: Health status
- `message`: Descriptive message
- `connected`: Boolean indicating connection state

### 2. Disk Space
Monitors available disk space for critical directories.

**Healthy Criteria:**
- Database directory has < 90% disk usage
- Upload directory has < 90% disk usage

**Warning Criteria:**
- Either directory has ≥ 90% disk usage

**Response Fields:**
- `status`: Health status
- `database_directory`: Disk usage for database storage
- `upload_directory`: Disk usage for file uploads
  - `path`: Directory path
  - `total_gb`: Total disk space in GB
  - `used_gb`: Used disk space in GB
  - `free_gb`: Free disk space in GB
  - `percent_used`: Percentage of disk space used

### 3. Uptime
Reports how long the application has been running.

**Response Fields:**
- `status`: Health status
- `started_at`: ISO 8601 timestamp of application start
- `uptime_seconds`: Uptime in seconds
- `uptime_formatted`: Human-readable uptime (e.g., "5d 3h 24m 15s")

## Usage Examples

### cURL
```bash
curl http://localhost:8000/health
```

### PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```

### Python
```python
import requests

response = requests.get("http://localhost:8000/health")
health_status = response.json()

if health_status["status"] == "healthy":
    print("System is healthy")
else:
    print(f"System is unhealthy: {health_status}")
```

## Monitoring Integration

### Windows Task Scheduler
Create a scheduled task to check health periodically:

```powershell
# health_check.ps1
$response = Invoke-RestMethod -Uri "http://localhost:8000/health"

if ($response.status -ne "healthy") {
    # Send alert (email, log, etc.)
    Write-EventLog -LogName Application -Source "MailroomTracking" `
        -EventId 1001 -EntryType Warning `
        -Message "Health check failed: $($response.status)"
}
```

### Nagios/Icinga
```bash
#!/bin/bash
# check_mailroom_health.sh

RESPONSE=$(curl -s http://localhost:8000/health)
STATUS=$(echo $RESPONSE | jq -r '.status')

if [ "$STATUS" = "healthy" ]; then
    echo "OK - Mailroom system is healthy"
    exit 0
else
    echo "CRITICAL - Mailroom system is $STATUS"
    exit 2
fi
```

### Prometheus
The endpoint can be scraped by Prometheus with a custom exporter or using the JSON exporter.

## Troubleshooting

### Database Unhealthy
If the database check fails:
1. Verify the database file exists at the configured path
2. Check file permissions
3. Ensure no other process has locked the database
4. Review application logs for database errors

### Disk Space Warning
If disk space exceeds 90%:
1. Review and clean up old backup files
2. Archive or delete old package photos
3. Consider moving storage to a larger volume

### Application Not Responding
If the health endpoint doesn't respond:
1. Check if the application process is running
2. Verify the application is listening on the correct port
3. Check Windows Firewall rules
4. Review application startup logs

## Related Documentation
- [Deployment Guide](DEPLOYMENT.md)
- [Configuration Guide](CONFIGURATION.md)
- [Caddy Setup](CADDY_SETUP.md)
