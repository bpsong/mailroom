# Configuration Reference

## Overview

The Mailroom Tracking System is configured through environment variables defined in a `.env` file. This document provides a comprehensive reference for all configuration parameters.

**Configuration File**: `.env` (located in application root directory)  
**Format**: KEY=VALUE (one per line)  
**Encoding**: UTF-8  
**Comments**: Lines starting with `#` are ignored

## Quick Start

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your settings:
   ```bash
   notepad .env  # Windows
   ```

3. Restart the application to apply changes:
   ```powershell
   Restart-Service MailroomTracking
   ```

## Configuration Sections

### Application Settings

#### APP_ENV

**Description**: Application environment mode  
**Type**: String (enum)  
**Default**: `development`  
**Valid Values**: `development`, `production`, `testing`  
**Required**: No

**Behavior by Environment**:

| Environment | Debug Mode | Logging Level | Validation |
|-------------|------------|---------------|------------|
| development | Enabled | DEBUG | Relaxed |
| production | Disabled | INFO | Strict |
| testing | Disabled | WARNING | Relaxed |

**Example**:
```env
APP_ENV=production
```

**Notes**:
- In production mode, SECRET_KEY must be at least 32 characters
- Development mode enables detailed error messages
- Testing mode is used for automated tests

---

#### APP_HOST

**Description**: Host address to bind the application server  
**Type**: String (IP address)  
**Default**: `0.0.0.0`  
**Required**: No

**Common Values**:
- `0.0.0.0` - Listen on all network interfaces (recommended for production behind reverse proxy)
- `127.0.0.1` - Listen only on localhost (for development)
- `<specific-ip>` - Listen on specific network interface

**Example**:
```env
APP_HOST=0.0.0.0
```

**Security Note**: When using `0.0.0.0`, ensure the application is behind a reverse proxy (Caddy) and firewall rules are properly configured.

---

#### APP_PORT

**Description**: Port number for the application server  
**Type**: Integer  
**Default**: `8000`  
**Range**: 1-65535  
**Required**: No

**Example**:
```env
APP_PORT=8000
```

**Notes**:
- Default port 8000 is recommended
- If changing, update Caddy configuration and firewall rules
- Ports below 1024 require administrator privileges

---

#### SECRET_KEY

**Description**: Secret key for session encryption and CSRF tokens  
**Type**: String  
**Default**: None  
**Minimum Length**: 32 characters (production), 16 characters (development)  
**Required**: Yes

**Generation**:
```powershell
# Generate secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example**:
```env
SECRET_KEY=your-secure-random-key-min-32-characters-long
```

**Security Requirements**:
- Must be cryptographically random
- Must be unique per installation
- Must never be committed to version control
- Must be at least 32 characters in production
- Should be rotated periodically (requires re-login for all users)

---

### Database Settings

#### DATABASE_PATH

**Description**: Path to DuckDB database file  
**Type**: String (file path)  
**Default**: `./data/mailroom.duckdb`  
**Required**: No

**Path Types**:
- Relative path: `./data/mailroom.duckdb` (relative to application root)
- Absolute path: `C:\MailroomApp\data\mailroom.duckdb`

**Example**:
```env
DATABASE_PATH=./data/mailroom.duckdb
```

**Notes**:
- Parent directory must exist or be creatable
- Service account must have read/write permissions
- Database file is created automatically on first run
- WAL files (`.wal`) are created in same directory

---

#### DATABASE_CHECKPOINT_INTERVAL

**Description**: Interval in seconds between database checkpoints  
**Type**: Integer  
**Default**: `300` (5 minutes)  
**Range**: 60-3600  
**Required**: No

**Example**:
```env
DATABASE_CHECKPOINT_INTERVAL=300
```

**Tuning Guidelines**:
- Lower values (60-180): Better crash recovery, more I/O overhead
- Higher values (300-600): Better write performance, longer recovery time
- Recommended: 300 for balanced performance

---

### File Storage Settings

#### UPLOAD_DIR

**Description**: Directory for uploaded files (package photos)  
**Type**: String (directory path)  
**Default**: `./uploads`  
**Required**: No

**Example**:
```env
UPLOAD_DIR=./uploads
```

**Directory Structure**:
```
uploads/
  packages/
    2024/
      01/
        <uuid>-photo1.jpg
        <uuid>-photo2.png
```

**Notes**:
- Directory is created automatically if it doesn't exist
- Service account must have read/write permissions
- Files are organized by year/month for easier management
- Consider separate disk/volume for large deployments

---

#### MAX_UPLOAD_SIZE

**Description**: Maximum file size for uploads in bytes  
**Type**: Integer  
**Default**: `5242880` (5 MB)  
**Range**: 1048576-10485760 (1 MB - 10 MB)  
**Required**: No

**Example**:
```env
MAX_UPLOAD_SIZE=5242880
```

**Common Values**:
- `5242880` - 5 MB (recommended)
- `10485760` - 10 MB (for high-resolution photos)
- `2097152` - 2 MB (for limited storage)

**Notes**:
- Larger files increase storage requirements and upload time
- Consider network bandwidth when setting this value
- Mobile uploads may be slower with larger limits

---

#### ALLOWED_IMAGE_TYPES

**Description**: Comma-separated list of allowed MIME types for image uploads  
**Type**: String (comma-separated)  
**Default**: `image/jpeg,image/png,image/webp`  
**Required**: No

**Example**:
```env
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp
```

**Supported Types**:
- `image/jpeg` - JPEG/JPG images
- `image/png` - PNG images
- `image/webp` - WebP images (modern format, smaller file sizes)

**Notes**:
- File type is validated by content, not just extension
- WebP provides better compression than JPEG/PNG
- All modern browsers support these formats

---

### Security Settings

#### SESSION_TIMEOUT

**Description**: Session inactivity timeout in seconds  
**Type**: Integer  
**Default**: `1800` (30 minutes)  
**Range**: 300-7200 (5 minutes - 2 hours)  
**Required**: No

**Example**:
```env
SESSION_TIMEOUT=1800
```

**Tuning Guidelines**:
- Shorter timeout (300-900): Higher security, more frequent logins
- Longer timeout (1800-3600): Better user experience, lower security
- Recommended: 1800 (30 minutes) for balanced security

**Notes**:
- Session extends on each request
- Users are redirected to login when session expires
- Active sessions are not affected by configuration changes

---

#### MAX_CONCURRENT_SESSIONS

**Description**: Maximum number of concurrent sessions per user  
**Type**: Integer  
**Default**: `3`  
**Range**: 1-10  
**Required**: No

**Example**:
```env
MAX_CONCURRENT_SESSIONS=3
```

**Notes**:
- Prevents session hijacking and credential sharing
- Oldest session is terminated when limit is exceeded
- Set to 1 for maximum security (single device per user)
- Set to 3-5 for users with multiple devices

---

#### MAX_FAILED_LOGINS

**Description**: Maximum failed login attempts before account lockout  
**Type**: Integer  
**Default**: `5`  
**Range**: 3-10  
**Required**: No

**Example**:
```env
MAX_FAILED_LOGINS=5
```

**Notes**:
- Counter resets on successful login
- Lockout duration is controlled by ACCOUNT_LOCKOUT_DURATION
- Failed attempts are logged in auth_events table

---

#### ACCOUNT_LOCKOUT_DURATION

**Description**: Account lockout duration in seconds after exceeding failed login attempts  
**Type**: Integer  
**Default**: `1800` (30 minutes)  
**Range**: 300-3600 (5 minutes - 1 hour)  
**Required**: No

**Example**:
```env
ACCOUNT_LOCKOUT_DURATION=1800
```

**Notes**:
- Account automatically unlocks after duration expires
- Super admin can manually unlock accounts
- Lockout events are logged in auth_events table

---

#### PASSWORD_MIN_LENGTH

**Description**: Minimum password length requirement  
**Type**: Integer  
**Default**: `12`  
**Range**: 8-32  
**Required**: No

**Example**:
```env
PASSWORD_MIN_LENGTH=12
```

**Security Recommendations**:
- Minimum 12 characters (recommended)
- 14-16 characters for high-security environments
- Combined with complexity requirements (uppercase, lowercase, digits, symbols)

---

#### PASSWORD_HISTORY_COUNT

**Description**: Number of previous passwords to prevent reuse  
**Type**: Integer  
**Default**: `3`  
**Range**: 0-10  
**Required**: No

**Example**:
```env
PASSWORD_HISTORY_COUNT=3
```

**Notes**:
- Set to 0 to disable password history checking
- Higher values increase security but may frustrate users
- Password hashes are stored in users.password_history (JSON array)

---

### Argon2 Password Hashing Settings

#### ARGON2_TIME_COST

**Description**: Number of iterations for Argon2 hashing  
**Type**: Integer  
**Default**: `3`  
**Range**: 1-10  
**Required**: No

**Example**:
```env
ARGON2_TIME_COST=3
```

**Performance Impact**:
- Higher values = slower hashing = better security
- Each increment roughly doubles computation time
- Recommended: 3 for balanced security/performance

**Tuning**:
- Increase if server has spare CPU capacity
- Decrease if login times are too slow (> 500ms)

---

#### ARGON2_MEMORY_COST

**Description**: Memory usage for Argon2 hashing in KiB  
**Type**: Integer  
**Default**: `19456` (19 MB)  
**Range**: 8192-65536 (8 MB - 64 MB)  
**Required**: No

**Example**:
```env
ARGON2_MEMORY_COST=19456
```

**Notes**:
- Higher values = more memory-hard = better security against GPU attacks
- Recommended: 19456 (19 MB) for balanced security
- Ensure server has sufficient RAM for concurrent logins

---

#### ARGON2_PARALLELISM

**Description**: Number of parallel threads for Argon2 hashing  
**Type**: Integer  
**Default**: `1`  
**Range**: 1-4  
**Required**: No

**Example**:
```env
ARGON2_PARALLELISM=1
```

**Notes**:
- Higher values use more CPU cores
- Recommended: 1 for single-threaded consistency
- Increase only if server has many CPU cores and high login volume

---

### Rate Limiting Settings

#### RATE_LIMIT_LOGIN

**Description**: Maximum login requests per minute per IP address  
**Type**: Integer  
**Default**: `10`  
**Range**: 5-60  
**Required**: No

**Example**:
```env
RATE_LIMIT_LOGIN=10
```

**Notes**:
- Prevents brute-force attacks
- Applies per IP address
- Legitimate users rarely exceed this limit
- Consider network architecture (NAT, proxy) when setting

---

#### RATE_LIMIT_API

**Description**: Maximum API requests per minute per authenticated user  
**Type**: Integer  
**Default**: `100`  
**Range**: 50-1000  
**Required**: No

**Example**:
```env
RATE_LIMIT_API=100
```

**Notes**:
- Prevents API abuse
- Applies per authenticated user
- Normal usage rarely exceeds 100 requests/minute
- Increase for high-volume automated operations

---

### Logging Settings

#### LOG_LEVEL

**Description**: Minimum logging level  
**Type**: String (enum)  
**Default**: `INFO`  
**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`  
**Required**: No

**Example**:
```env
LOG_LEVEL=INFO
```

**Log Levels**:
- `DEBUG` - Detailed diagnostic information (development only)
- `INFO` - General informational messages (recommended for production)
- `WARNING` - Warning messages for potential issues
- `ERROR` - Error messages for failures
- `CRITICAL` - Critical errors requiring immediate attention

**Notes**:
- Lower levels include all higher levels (DEBUG includes everything)
- Use INFO for production to balance detail and performance
- Use DEBUG only for troubleshooting (generates large log files)

---

#### LOG_FILE

**Description**: Path to application log file  
**Type**: String (file path)  
**Default**: `./logs/mailroom.log`  
**Required**: No

**Example**:
```env
LOG_FILE=./logs/mailroom.log
```

**Notes**:
- Parent directory must exist or be creatable
- Service account must have write permissions
- Logs are automatically rotated based on LOG_ROTATION setting

---

#### LOG_ROTATION

**Description**: Log file rotation frequency  
**Type**: String (enum)  
**Default**: `weekly`  
**Valid Values**: `daily`, `weekly`, `monthly`  
**Required**: No

**Example**:
```env
LOG_ROTATION=weekly
```

**Rotation Behavior**:
- `daily` - New log file each day (mailroom-YYYYMMDD.log)
- `weekly` - New log file each week (mailroom-YYYYWW.log)
- `monthly` - New log file each month (mailroom-YYYYMM.log)

**Notes**:
- Old log files are automatically archived
- Rotation occurs at midnight (local time)
- Consider disk space when choosing rotation frequency

---

#### LOG_RETENTION_DAYS

**Description**: Number of days to retain log files  
**Type**: Integer  
**Default**: `365`  
**Range**: 30-3650 (1 month - 10 years)  
**Required**: No

**Example**:
```env
LOG_RETENTION_DAYS=365
```

**Notes**:
- Audit logs (auth_events) are retained separately in database
- Application logs are deleted after retention period
- Compliance requirements may dictate minimum retention
- Consider disk space when setting retention period

---

### HTTPS/TLS Settings

#### DOMAIN

**Description**: Domain name for the application  
**Type**: String (domain name)  
**Default**: `mailroom.company.local`  
**Required**: No (but recommended for production)

**Example**:
```env
DOMAIN=mailroom.company.local
```

**Notes**:
- Used by Caddy for HTTPS configuration
- Must match DNS entry
- Must match TLS certificate Common Name (CN)
- Can be IP address for testing (not recommended for production)

---

#### TLS_CERT_PATH

**Description**: Path to TLS certificate file (PEM format)  
**Type**: String (file path)  
**Default**: `./certs/cert.pem`  
**Required**: No (if using Caddy automatic HTTPS)

**Example**:
```env
TLS_CERT_PATH=./certs/cert.pem
```

**Notes**:
- Must be in PEM format
- Can be self-signed (for testing) or from internal CA (for production)
- Must match DOMAIN setting
- File must be readable by Caddy service account

---

#### TLS_KEY_PATH

**Description**: Path to TLS private key file (PEM format)  
**Type**: String (file path)  
**Default**: `./certs/key.pem`  
**Required**: No (if using Caddy automatic HTTPS)

**Example**:
```env
TLS_KEY_PATH=./certs/key.pem
```

**Security Notes**:
- Must be kept secure (restrict file permissions)
- Should not be readable by unauthorized users
- Should not be committed to version control
- Should be backed up securely

---

## Environment-Specific Configurations

### Development Configuration

```env
# Development environment
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
SECRET_KEY=dev-secret-key-change-in-production

# Database
DATABASE_PATH=./data/mailroom-dev.duckdb

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=./logs/mailroom-dev.log

# Security (relaxed for development)
SESSION_TIMEOUT=3600
MAX_FAILED_LOGINS=10
PASSWORD_MIN_LENGTH=8
```

### Production Configuration

```env
# Production environment
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=<generate-secure-random-key-min-32-chars>

# Database
DATABASE_PATH=./data/mailroom.duckdb
DATABASE_CHECKPOINT_INTERVAL=300

# File Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=5242880

# Security
SESSION_TIMEOUT=1800
MAX_CONCURRENT_SESSIONS=3
MAX_FAILED_LOGINS=5
ACCOUNT_LOCKOUT_DURATION=1800
PASSWORD_MIN_LENGTH=12
PASSWORD_HISTORY_COUNT=3

# Argon2
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=19456
ARGON2_PARALLELISM=1

# Rate Limiting
RATE_LIMIT_LOGIN=10
RATE_LIMIT_API=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/mailroom.log
LOG_ROTATION=weekly
LOG_RETENTION_DAYS=365

# HTTPS
DOMAIN=mailroom.company.local
TLS_CERT_PATH=./certs/cert.pem
TLS_KEY_PATH=./certs/key.pem
```

### Testing Configuration

```env
# Testing environment
APP_ENV=testing
APP_HOST=127.0.0.1
APP_PORT=8001
SECRET_KEY=test-secret-key

# Database (in-memory or separate test database)
DATABASE_PATH=:memory:

# Logging
LOG_LEVEL=WARNING
LOG_FILE=./logs/mailroom-test.log

# Security (relaxed for faster tests)
SESSION_TIMEOUT=3600
MAX_FAILED_LOGINS=10
ARGON2_TIME_COST=1
ARGON2_MEMORY_COST=8192
```

## Configuration Validation

The application validates configuration on startup. Common validation errors:

### Missing Required Configuration

**Error**: `SECRET_KEY must be set`

**Solution**: Add SECRET_KEY to .env file

### Invalid Configuration Value

**Error**: `APP_ENV must be one of: development, production, testing`

**Solution**: Use valid value for APP_ENV

### Insecure Production Configuration

**Error**: `SECRET_KEY must be at least 32 characters in production`

**Solution**: Generate secure SECRET_KEY with minimum 32 characters

### Invalid File Path

**Error**: `DATABASE_PATH directory does not exist`

**Solution**: Ensure parent directory exists or is creatable

## Configuration Best Practices

### Security

1. **Never commit .env to version control**
   - Add `.env` to `.gitignore`
   - Use `.env.example` as template

2. **Use strong SECRET_KEY**
   - Generate cryptographically random key
   - Minimum 32 characters in production
   - Rotate periodically

3. **Restrict file permissions**
   ```powershell
   icacls ".env" /inheritance:r /grant:r "MailroomService:R"
   ```

4. **Use environment-specific configurations**
   - Separate .env files for dev/staging/production
   - Never use development settings in production

### Performance

1. **Tune database checkpoint interval**
   - Balance between write performance and recovery time
   - Monitor I/O usage and adjust

2. **Adjust rate limits based on usage**
   - Monitor actual request rates
   - Set limits slightly above normal usage

3. **Optimize Argon2 parameters**
   - Target 200-500ms for password hashing
   - Balance security and user experience

### Maintenance

1. **Document custom configurations**
   - Keep notes on why values were changed
   - Include in deployment documentation

2. **Review configuration periodically**
   - Check for security updates
   - Adjust based on usage patterns

3. **Test configuration changes**
   - Test in development/staging first
   - Have rollback plan ready

## Troubleshooting Configuration Issues

### Application Won't Start

1. Check configuration validation errors in logs
2. Verify all required settings are present
3. Ensure file paths are correct and accessible
4. Validate SECRET_KEY length and format

### Performance Issues

1. Check LOG_LEVEL (DEBUG generates large logs)
2. Review DATABASE_CHECKPOINT_INTERVAL
3. Adjust Argon2 parameters if login is slow
4. Monitor rate limit settings

### Security Warnings

1. Ensure APP_ENV=production in production
2. Verify SECRET_KEY is secure and unique
3. Check TLS certificate validity
4. Review session timeout settings

## Configuration Change Checklist

Before changing configuration:

- [ ] Backup current .env file
- [ ] Document reason for change
- [ ] Test in development environment
- [ ] Review security implications
- [ ] Plan service restart window
- [ ] Notify users of potential downtime
- [ ] Monitor application after change
- [ ] Verify functionality
- [ ] Update documentation

## References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Argon2 Parameters](https://github.com/P-H-C/phc-winner-argon2#command-line-utility)
- [DuckDB Configuration](https://duckdb.org/docs/configuration/overview)
- [Caddy Configuration](https://caddyserver.com/docs/caddyfile)
