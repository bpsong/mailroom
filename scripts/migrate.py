"""Database migration CLI script."""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.migrations import MigrationManager, run_initial_migration
from app.config import settings


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Database migration tool for Mailroom Tracking System'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database with schema')
    init_parser.add_argument(
        '--no-super-admin',
        action='store_true',
        help='Skip creating super admin user'
    )
    init_parser.add_argument(
        '--username',
        default='admin',
        help='Super admin username (default: admin)'
    )
    init_parser.add_argument(
        '--password',
        default='ChangeMe123!',
        help='Super admin password (default: ChangeMe123!)'
    )
    init_parser.add_argument(
        '--full-name',
        default='System Administrator',
        help='Super admin full name (default: System Administrator)'
    )
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset database (WARNING: deletes all data)')
    reset_parser.add_argument(
        '--confirm',
        action='store_true',
        required=True,
        help='Confirm database reset'
    )
    
    # Bootstrap command
    bootstrap_parser = subparsers.add_parser('bootstrap', help='Create super admin user')
    bootstrap_parser.add_argument(
        '--username',
        default='admin',
        help='Super admin username (default: admin)'
    )
    bootstrap_parser.add_argument(
        '--password',
        default='ChangeMe123!',
        help='Super admin password (default: ChangeMe123!)'
    )
    bootstrap_parser.add_argument(
        '--full-name',
        default='System Administrator',
        help='Super admin full name (default: System Administrator)'
    )
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify database schema')
    
    # Common arguments
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Execute command
    if args.command == 'init':
        print(f"Initializing database at: {settings.database_path}")
        run_initial_migration(
            create_super_admin=not args.no_super_admin,
            super_admin_username=args.username,
            super_admin_password=args.password,
            super_admin_full_name=args.full_name
        )
        print("Database initialization complete!")
        
        if not args.no_super_admin:
            print(f"\nSuper admin credentials:")
            print(f"  Username: {args.username}")
            print(f"  Password: {args.password}")
            print(f"\n⚠️  IMPORTANT: Change the password on first login!")
    
    elif args.command == 'reset':
        if not args.confirm:
            print("ERROR: --confirm flag is required to reset database")
            sys.exit(1)
        
        print(f"Resetting database at: {settings.database_path}")
        print("⚠️  WARNING: This will delete all data!")
        
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Reset cancelled")
            sys.exit(0)
        
        manager = MigrationManager(settings.database_path)
        manager.reset_database()
        print("Database reset complete!")
    
    elif args.command == 'bootstrap':
        print(f"Creating super admin user in: {settings.database_path}")
        manager = MigrationManager(settings.database_path)
        
        created = manager.bootstrap_super_admin(
            username=args.username,
            password=args.password,
            full_name=args.full_name
        )
        
        if created:
            print(f"\nSuper admin credentials:")
            print(f"  Username: {args.username}")
            print(f"  Password: {args.password}")
            print(f"\n⚠️  IMPORTANT: Change the password on first login!")
        else:
            print("Super admin user already exists or users table is not empty")
    
    elif args.command == 'verify':
        print(f"Verifying database schema at: {settings.database_path}")
        from app.database.schema import verify_schema
        
        if verify_schema(settings.database_path):
            print("✓ Schema verification passed - all tables exist")
        else:
            print("✗ Schema verification failed - some tables are missing")
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
