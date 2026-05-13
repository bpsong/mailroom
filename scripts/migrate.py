"""Database migration CLI script."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database.migrations import MigrationManager, run_initial_migration


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_bootstrap_result(result) -> None:
    """Print first-admin credentials returned by bootstrap."""
    if result and result.created:
        print("\nInitial super admin credentials:")
        print(f"  Username: {result.username}")
        print(f"  Temporary password: {result.password}")
        print("\nThis password is shown once. Store it securely and change it on first login.")
    else:
        print("\nNo super admin was created because the users table is not empty.")


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration tool for Mailroom Tracking System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    init_parser = subparsers.add_parser("init", help="Initialize database with schema")
    init_parser.add_argument(
        "--no-super-admin",
        action="store_true",
        help="Skip creating the first super admin user",
    )
    init_parser.add_argument(
        "--username",
        default="admin",
        help="Super admin username (default: admin)",
    )
    init_parser.add_argument(
        "--password",
        default=None,
        help="Super admin temporary password (default: generate a random one-time password)",
    )
    init_parser.add_argument(
        "--full-name",
        default="System Administrator",
        help="Super admin full name (default: System Administrator)",
    )

    reset_parser = subparsers.add_parser("reset", help="Reset database (WARNING: deletes all data)")
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="Confirm database reset",
    )

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Create first super admin user")
    bootstrap_parser.add_argument(
        "--username",
        default="admin",
        help="Super admin username (default: admin)",
    )
    bootstrap_parser.add_argument(
        "--password",
        default=None,
        help="Super admin temporary password (default: generate a random one-time password)",
    )
    bootstrap_parser.add_argument(
        "--full-name",
        default="System Administrator",
        help="Super admin full name (default: System Administrator)",
    )

    subparsers.add_parser("verify", help="Verify database schema")

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "init":
        print(f"Initializing database at: {settings.database_path}")
        result = run_initial_migration(
            create_super_admin=not args.no_super_admin,
            super_admin_username=args.username,
            super_admin_password=args.password,
            super_admin_full_name=args.full_name,
        )
        print("Database initialization complete!")
        if not args.no_super_admin:
            print_bootstrap_result(result)
        return 0

    if args.command == "reset":
        print(f"Resetting database at: {settings.database_path}")
        print("WARNING: This will delete all data!")

        response = input("Type 'yes' to confirm: ")
        if response.lower() != "yes":
            print("Reset cancelled")
            return 0

        manager = MigrationManager(settings.database_path)
        manager.reset_database()
        print("Database reset complete!")
        return 0

    if args.command == "bootstrap":
        print(f"Creating super admin user in: {settings.database_path}")
        manager = MigrationManager(settings.database_path)
        manager.run_migrations()
        result = manager.bootstrap_super_admin(
            username=args.username,
            password=args.password,
            full_name=args.full_name,
        )

        print_bootstrap_result(result)
        return 0 if result.created else 1

    if args.command == "verify":
        print(f"Verifying database schema at: {settings.database_path}")
        from app.database.schema import verify_schema

        if verify_schema(settings.database_path):
            print("Schema verification passed - all tables exist")
            return 0

        print("Schema verification failed - some tables are missing")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
