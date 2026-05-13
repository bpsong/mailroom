# Initial Super Admin Bootstrap

Fresh deployments start with an empty `users` table. The application does not create a
known default account during normal startup. Create the first `super_admin` explicitly
from the installer shell after `.env` is configured.

## Recommended Command

```powershell
C:\Python313\python.exe .\scripts\bootstrap_super_admin.py
```

The command initializes the schema if needed, creates `admin` as the first super admin,
generates a temporary password, and prints it once:

```text
Initial super admin created.

Username: admin
Temporary password: <generated-password>

This password is shown once. Store it securely and change it on first login.
```

## Custom Username Or Password

```powershell
C:\Python313\python.exe .\scripts\bootstrap_super_admin.py --username superadmin --full-name "System Administrator"
```

To supply a temporary password yourself:

```powershell
C:\Python313\python.exe .\scripts\bootstrap_super_admin.py --password "Use-A-Unique-Temporary-Password"
```

## Startup Behavior

- Development/testing startup logs a warning if no users exist.
- Production startup fails if no users exist. Run the bootstrap command first.
- The bootstrap command refuses to create another account once any user exists.
- The temporary password is hashed before storage and is never logged by application logging.
- The first super admin is created with `must_change_password = 1`.
