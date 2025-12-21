# Mailroom Tracking System

A secure, mobile-friendly web application for tracking packages and managing mailroom operations in corporate environments. Built with FastAPI, DuckDB, and modern web technologies for reliable offline operation behind corporate firewalls.

## Overview

The Mailroom Tracking System streamlines package management for mailroom staff with features designed for speed, security, and ease of use. The system operates entirely on-premises on Windows Server with no external dependencies, making it ideal for secure corporate environments.

### Key Features

- **Role-Based Access Control**: Three user roles (Super Admin, Admin, Operator) with granular permissions
- **Package Lifecycle Tracking**: Register, track, and manage packages from arrival to delivery
- **Recipient Management**: Maintain employee directory with CSV bulk import capability
- **Mobile-First Design**: Responsive interface optimized for tablets and phones with camera integration
- **QR Code Stickers**: Generate, download, and print 2 cm x 2 cm high-error-correction QR codes that deep-link to package details for fast mobile scanning
- **Comprehensive Audit Logging**: Track all system actions for security and compliance
- **Secure Authentication**: Argon2id password hashing, session management, and account lockout protection
- **Offline Operation**: Fully functional without internet connectivity using embedded DuckDB database
- **Dashboard & Reporting**: Real-time statistics and CSV export capabilities

### Technology Stack

- **Backend**: FastAPI (Python 3.12+) with async support
- **Database**: DuckDB (embedded, single-file)
- **Frontend**: HTMX + TailwindCSS 3.4 + daisyUI 4.12
- **Authentication**: Argon2-cffi with secure session management
- **Deployment**: Windows Service (NSSM) + Caddy reverse proxy

> **Note:** `daisyui.md` ships with the official DaisyUI 5 / TailwindCSS 4 reference for AI tooling, but the production build is currently pinned to TailwindCSS 3.4.0 and DaisyUI 4.12.0. Generated markup should stick to classes that exist in these shipped versions.

## Quick Start

### Prerequisites

- **Python 3.12 or higher** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18 or higher** - [Download Node.js](https://nodejs.org/)
- **Git** (optional) - For cloning the repository

### Development Setup

1. **Clone or download the repository**
   ```bash
   git clone <repository-url>
   cd mailroom-tracking
   ```

2. **Create and activate a Python virtual environment**
   
   Windows (PowerShell):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   
   Windows (Command Prompt):
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
   
   Linux/Mac:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -e .
   ```
   
   For development with testing tools:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install Node.js dependencies**
   ```bash
   npm install
   ```

5. **Build TailwindCSS**
   ```bash
   npm run build:css
   ```

6. **Configure environment variables**
   
   Windows:
   ```cmd
   copy .env.example .env
   ```
   
   Linux/Mac:
   ```bash
   cp .env.example .env
   ```
   
   **IMPORTANT**: Edit `.env` and set a secure `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

7. **Initialize the database**
   
   Windows:
   ```powershell
   .\scripts\init_database.ps1
   ```
   
   Or manually with Python:
   ```bash
   python -c "from app.database.init_db import init_database; init_database()"
   ```
   
   This creates the database schema and a super admin account. **Save the credentials securely!**

8. **Start the development server**
   
   Terminal 1 - TailwindCSS watcher (auto-rebuild CSS on changes):
   ```bash
   npm run watch:css
   ```
   
   Terminal 2 - FastAPI application:
   ```bash
   python -m app.main
   ```
   
   Or with uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

9. **Access the application**
   
   Open your browser to: `http://localhost:8000`
   
   Login with the super admin credentials created in step 7.

## Project Structure

```
mailroom-tracking/
├── app/                          # Application source code
│   ├── database/                 # Database layer
│   │   ├── init_db.py           # Schema initialization
│   │   └── service.py           # Database service with write queue
│   ├── decorators/              # Route decorators
│   │   └── auth.py              # Authentication & RBAC decorators
│   ├── middleware/              # FastAPI middleware
│   │   ├── auth.py              # Session validation
│   │   ├── csrf.py              # CSRF protection
│   │   └── rate_limit.py        # Rate limiting
│   ├── models/                  # Pydantic models
│   │   ├── user.py              # User models
│   │   ├── package.py           # Package models
│   │   └── recipient.py         # Recipient models
│   ├── routes/                  # API route handlers
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── packages.py          # Package management
│   │   ├── recipients.py        # Recipient management
│   │   ├── admin.py             # Admin endpoints
│   │   └── dashboard.py         # Dashboard & reports
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py      # Authentication & password hashing
│   │   ├── rbac_service.py      # Role-based access control
│   │   ├── user_service.py      # User management
│   │   ├── package_service.py   # Package operations
│   │   ├── recipient_service.py # Recipient operations
│   │   ├── file_service.py      # File upload handling
│   │   ├── audit_service.py     # Audit logging
│   │   └── dashboard_service.py # Dashboard statistics
│   ├── utils/                   # Utility functions
│   │   ├── validators.py        # Input validation
│   │   └── helpers.py           # Helper functions
│   ├── config.py                # Configuration management
│   ├── main.py                  # FastAPI application entry point
│   └── __init__.py
├── static/                      # Static assets
│   ├── css/
│   │   ├── input.css            # TailwindCSS source
│   │   └── output.css           # Compiled CSS (generated)
│   └── js/
│       └── app.js               # Frontend JavaScript
├── templates/                   # Jinja2 HTML templates
│   ├── admin/                   # Admin pages
│   ├── components/              # Reusable components
│   ├── dashboard/               # Dashboard pages
│   ├── packages/                # Package pages
│   ├── user/                    # User management pages
│   └── base.html                # Base template
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   ├── conftest.py              # Pytest fixtures
│   └── __init__.py
├── scripts/                     # Deployment scripts (PowerShell)
│   ├── init_database.ps1        # Database initialization
│   ├── install_service.ps1      # Windows Service installation
│   ├── backup.ps1               # Backup script
│   ├── cleanup_backups.ps1      # Backup cleanup
│   └── README.md                # Scripts documentation
├── docs/                        # Documentation
│   ├── API_DOCUMENTATION.md     # API reference
│   ├── DATABASE_SCHEMA.md       # Database schema
│   ├── DEPLOYMENT.md            # Deployment guide
│   ├── CONFIGURATION.md         # Configuration reference
│   ├── USER_GUIDE_*.md          # User guides by role
│   └── SECURITY_IMPLEMENTATION.md
├── data/                        # Database files (created at runtime)
│   └── mailroom.duckdb          # DuckDB database
├── uploads/                     # Uploaded package photos (created at runtime)
├── logs/                        # Application logs (created at runtime)
│   └── mailroom.log
├── .env.example                 # Example environment configuration
├── .env                         # Environment configuration (create from .env.example)
├── .gitignore
├── pyproject.toml               # Python project configuration
├── package.json                 # Node.js configuration
├── tailwind.config.js           # TailwindCSS configuration
├── Caddyfile                    # Caddy reverse proxy config
└── README.md                    # This file
```

## Dependencies

### Python Dependencies (pyproject.toml)

**Core Dependencies:**
- `fastapi>=0.104.0` - Modern web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `duckdb>=0.9.0` - Embedded SQL database
- `jinja2>=3.1.0` - Template engine
- `argon2-cffi>=23.1.0` - Password hashing
- `python-multipart>=0.0.6` - File upload support
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Settings management
- `python-dotenv>=1.0.0` - Environment variable loading
- `python-magic>=0.4.27` - File type detection

**Note**: Session management uses random tokens stored in DuckDB, not itsdangerous.

**Development Dependencies:**
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `httpx>=0.25.0` - HTTP client for testing
- `black>=23.0.0` - Code formatter
- `ruff>=0.1.0` - Linter

### Node.js Dependencies (package.json)

- `tailwindcss>=3.4.0` - CSS framework
- `daisyui>=4.12.0` - Component library

## Configuration

The application is configured via environment variables in the `.env` file. See `.env.example` for all available options.

### Essential Configuration

```env
# REQUIRED: Generate a secure secret key
SECRET_KEY=<generate-with-python-secrets>

# Application settings
APP_ENV=development          # development, production, or testing
APP_HOST=0.0.0.0            # Bind address
APP_PORT=8000               # Port number

# Database
DATABASE_PATH=./data/mailroom.duckdb

# File uploads
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=5242880     # 5MB in bytes

# Security
SESSION_TIMEOUT=1800        # 30 minutes
MAX_FAILED_LOGINS=5
ACCOUNT_LOCKOUT_DURATION=1800
PASSWORD_MIN_LENGTH=12

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/mailroom.log
```

For complete configuration reference, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

### QR Code Base URL Setting

- Managed inside the application under **Admin → System Settings** (Super Admin only).
- Enter the production hostname that operators use when scanning stickers (for example, `https://mailroom.company.local`).
- The value must start with `http://` or `https://` and is stored in the `system_settings` table; every QR sticker uses this host when constructing the package detail URL.

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/unit/test_auth_service.py
```

### Run Tests with Verbose Output

```bash
pytest -v
```

## Production Deployment

### Windows Server Deployment

The application is designed for deployment on Windows Server as a Windows Service.

#### Prerequisites

- Windows Server 2016 or higher
- Python 3.12+ installed
- NSSM (Non-Sucking Service Manager) - `choco install nssm`
- Caddy web server (for HTTPS) - `choco install caddy`

#### Deployment Steps

1. **Deploy application files** to `C:\MailroomApp`

2. **Install Python dependencies**
   ```powershell
   cd C:\MailroomApp
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -e .
   ```

3. **Install Node.js dependencies and build CSS**
   ```powershell
   npm install
   npm run build:css
   ```

4. **Create production .env file**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env with production settings
   ```

5. **Initialize database**
   ```powershell
   .\scripts\init_database.ps1
   ```

6. **Install as Windows Service**
   ```powershell
   .\scripts\install_service.ps1
   ```

7. **Configure Caddy for HTTPS**
   ```powershell
   # Edit Caddyfile with your domain
   caddy start
   ```

8. **Start the service**
   ```powershell
   Start-Service MailroomTracking
   ```

For detailed deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Backup and Maintenance

#### Create Backup

```powershell
.\scripts\backup.ps1
```

Backups include:
- DuckDB database (including WAL files)
- Uploaded package photos
- Configuration files

#### Cleanup Old Backups

```powershell
# Preview cleanup (dry run)
.\scripts\cleanup_backups.ps1 -DryRun

# Remove backups older than 30 days
.\scripts\cleanup_backups.ps1
```

#### Schedule Automated Backups

Set up Windows Task Scheduler for daily backups:

```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\MailroomApp\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
Register-ScheduledTask -TaskName "MailroomBackup" -Action $action -Trigger $trigger -Principal $principal
```

For complete maintenance procedures, see [scripts/README.md](scripts/README.md).

## Usage

### User Roles

1. **Super Admin**
   - Full system access
   - Manage all users including admins
   - View audit logs
   - System configuration

2. **Admin**
   - Manage operators
   - Manage recipients (add, edit, CSV import)
   - View reports and export data
   - All operator capabilities

3. **Operator**
   - Register packages
   - Update package status
   - Search packages
   - View dashboard

### Common Workflows

#### Register a Package (Operator)

1. Navigate to "Register Package"
2. Enter tracking number and carrier
3. Search and select recipient
4. Optionally attach photo
5. Click "Register Package"

#### Print a QR Code Sticker (Operator)

1. Go to "Packages" and find the package row/card.
2. Click or tap the "QR Actions" dropdown.
3. Choose "Download QR Code" to save `qr_code_{package_id}.png`, or choose "Print QR Code" to open the 2 cm × 2 cm sticker view in a new tab.
4. Use the browser's print dialog to send the sticker to a label printer, then affix it to the physical package.
5. When a teammate scans the sticker, they'll be redirected through login (if needed) and land on that package's detail page for quick updates.

#### Import Recipients (Admin)

1. Navigate to "Recipients" → "Import CSV"
2. Upload CSV file with columns: employee_id, name, email, department
3. Review validation report
4. Confirm import

#### Create User Account (Admin)

1. Navigate to "Users" → "Add User"
2. Enter username, full name, and role
3. Set initial password
4. User must change password on first login

For detailed user guides, see:
- [docs/USER_GUIDE_OPERATOR.md](docs/USER_GUIDE_OPERATOR.md)
- [docs/USER_GUIDE_ADMIN.md](docs/USER_GUIDE_ADMIN.md)
- [docs/USER_GUIDE_SUPER_ADMIN.md](docs/USER_GUIDE_SUPER_ADMIN.md)

## Troubleshooting

### Common Issues

#### Application Won't Start

**Symptom**: Error when running `python -m app.main`

**Solutions**:
1. Verify Python version: `python --version` (must be 3.12+)
2. Ensure virtual environment is activated
3. Reinstall dependencies: `pip install -e .`
4. Check `.env` file exists and has valid `SECRET_KEY`
5. Check logs: `logs/mailroom.log`

#### Database Locked Error

**Symptom**: "database is locked" error

**Solutions**:
1. Ensure only one instance of the application is running
2. Check for stale lock files in `data/` directory
3. Restart the application
4. If persistent, check DuckDB WAL files: `data/mailroom.duckdb.wal`

#### CSS Not Loading

**Symptom**: Unstyled pages

**Solutions**:
1. Build CSS: `npm run build:css`
2. Check `static/css/output.css` exists
3. Clear browser cache
4. Verify TailwindCSS installed: `npm install`

#### Login Fails with Correct Credentials

**Symptom**: Cannot login despite correct password

**Solutions**:
1. Check if account is locked (wait 30 minutes or reset in database)
2. Verify user is active: `is_active = true` in database
3. Check session timeout settings in `.env`
4. Clear browser cookies
5. Check auth_events table for failed login details

#### File Upload Fails

**Symptom**: Error uploading package photos

**Solutions**:
1. Check file size (max 5MB by default)
2. Verify file type (JPEG, PNG, WebP only)
3. Ensure `uploads/` directory exists and is writable
4. Check `MAX_UPLOAD_SIZE` in `.env`
5. Verify disk space available

#### Service Won't Start (Windows)

**Symptom**: Windows Service fails to start

**Solutions**:
1. Check service status: `Get-Service MailroomTracking`
2. View service logs in Event Viewer
3. Verify Python path in service configuration
4. Check file permissions on installation directory
5. Ensure `.env` file exists with correct settings
6. Reinstall service: `.\scripts\install_service.ps1`

#### Port Already in Use

**Symptom**: "Address already in use" error

**Solutions**:
1. Check what's using port 8000: `netstat -ano | findstr :8000`
2. Change port in `.env`: `APP_PORT=8001`
3. Kill process using the port (if safe to do so)
4. Use a different port for development

#### HTTPS Certificate Issues

**Symptom**: Browser shows certificate warning

**Solutions**:
1. Verify Caddy is running: `caddy version`
2. Check Caddyfile configuration
3. Ensure domain resolves to server IP
4. Check firewall allows port 443
5. Review Caddy logs: `caddy logs`

### Getting Help

1. **Check Documentation**
   - [API Documentation](docs/API_DOCUMENTATION.md)
   - [Database Schema](docs/DATABASE_SCHEMA.md)
   - [Deployment Guide](docs/DEPLOYMENT.md)
   - [Configuration Reference](docs/CONFIGURATION.md)

2. **Check Logs**
   - Application logs: `logs/mailroom.log`
   - Windows Event Viewer (for service issues)
   - Caddy logs (for HTTPS issues)

3. **Database Inspection**
   ```python
   import duckdb
   conn = duckdb.connect('data/mailroom.duckdb')
   conn.execute("SELECT * FROM users").fetchall()
   ```

4. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```env
# In .env file
LOG_LEVEL=DEBUG
APP_ENV=development
```

Then restart the application and check `logs/mailroom.log` for detailed information.

## Security Considerations

- **Change default credentials** immediately after installation
- **Use strong SECRET_KEY** (minimum 32 characters, randomly generated)
- **Enable HTTPS** in production (use Caddy reverse proxy)
- **Regular backups** - Schedule daily automated backups
- **Keep dependencies updated** - Run `pip install --upgrade` periodically
- **Review audit logs** - Monitor auth_events table for suspicious activity
- **Restrict network access** - Use firewall rules to limit access
- **Secure .env file** - Restrict file permissions (read-only for service account)

For complete security documentation, see [docs/SECURITY_IMPLEMENTATION.md](docs/SECURITY_IMPLEMENTATION.md).

## Performance

### Expected Performance

- **Concurrent Users**: 10-20 simultaneous users
- **Database Size**: Up to 10,000 packages per year
- **Search Response**: < 200ms for typical queries
- **Page Load**: < 500ms on local network

### Optimization Tips

1. **Database Maintenance**
   ```sql
   -- Run monthly to optimize database
   VACUUM;
   ANALYZE;
   ```

2. **Log Rotation**
   - Logs rotate weekly by default
   - Adjust `LOG_ROTATION` in `.env` if needed

3. **Disk Space**
   - Monitor `uploads/` directory size
   - Archive old package photos if needed
   - Run backup cleanup regularly

## Contributing

This is an internal application. For changes or improvements:

1. Create a feature branch
2. Make changes with tests
3. Run test suite: `pytest`
4. Format code: `black app/ tests/`
5. Lint code: `ruff check app/ tests/`
6. Submit for review

## License

Internal use only. Proprietary and confidential.

## Additional Resources

- **API Reference**: [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)
- **Database Schema**: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Configuration Guide**: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **User Guides**: [docs/USER_GUIDE_*.md](docs/)
- **Scripts Documentation**: [scripts/README.md](scripts/README.md)

## Support

For technical support or questions:
1. Review this README and documentation in `docs/`
2. Check troubleshooting section above
3. Review application logs
4. Contact your system administrator

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Maintained By**: Internal IT Team
