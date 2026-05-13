"""Create the first super admin account with a one-time password."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database.migrations import MigrationManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the first Mailroom super admin account."
    )
    parser.add_argument("--username", default="admin", help="Super admin username.")
    parser.add_argument(
        "--password",
        help="Temporary password. If omitted, a random password is generated.",
    )
    parser.add_argument(
        "--full-name",
        default="System Administrator",
        help="Super admin full name.",
    )

    args = parser.parse_args()

    manager = MigrationManager(settings.database_path)
    manager.run_migrations()
    result = manager.bootstrap_super_admin(
        username=args.username,
        password=args.password,
        full_name=args.full_name,
    )

    if not result.created:
        print("No account was created because the users table is not empty.")
        print("Use the existing super admin account to manage users.")
        return 1

    print("Initial super admin created.")
    print("")
    print(f"Username: {result.username}")
    print(f"Temporary password: {result.password}")
    print("")
    print("This password is shown once. Store it securely and change it on first login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
