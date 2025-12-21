"""
Migration: Add UNIQUE constraint to recipients.email column

This migration adds a unique constraint to the email column in the recipients table.
Run this if you have an existing database without the email unique constraint.
"""

import duckdb
import sys
from pathlib import Path


def migrate(db_path: str):
    """
    Add unique constraint to recipients.email column.
    
    Args:
        db_path: Path to the DuckDB database file
    """
    print(f"Migrating database: {db_path}")
    
    conn = duckdb.connect(db_path)
    try:
        conn.execute("BEGIN TRANSACTION")
        
        # Check for duplicate emails first
        print("Checking for duplicate emails...")
        duplicates = conn.execute("""
            SELECT email, COUNT(*) as count
            FROM recipients
            GROUP BY email
            HAVING COUNT(*) > 1
        """).fetchall()
        
        if duplicates:
            print("\nERROR: Found duplicate emails that must be resolved first:")
            for email, count in duplicates:
                print(f"  - {email}: {count} occurrences")
            print("\nPlease manually update or remove duplicate emails before running this migration.")
            conn.execute("ROLLBACK")
            return False
        
        print("No duplicate emails found.")
        
        # Check if packages table exists and has data
        print("Checking for existing packages...")
        package_count = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        print(f"Found {package_count} packages.")
        
        # Create a new table with the unique constraint
        print("Creating new table with unique constraint...")
        conn.execute("""
            CREATE TABLE recipients_new (
                id UUID PRIMARY KEY,
                employee_id VARCHAR NOT NULL UNIQUE,
                name VARCHAR NOT NULL,
                email VARCHAR NOT NULL UNIQUE,
                department VARCHAR,
                phone VARCHAR,
                location VARCHAR,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # Copy data from old table to new table
        print("Copying data to new table...")
        conn.execute("""
            INSERT INTO recipients_new
            SELECT * FROM recipients
        """)
        
        # Always handle packages table (even if empty) due to foreign key constraint
        print("Temporarily storing package data...")
        # Create temp table for packages
        conn.execute("""
            CREATE TEMP TABLE packages_temp AS 
            SELECT * FROM packages
        """)
        
        # Also store package_events if they exist
        print("Temporarily storing package events...")
        conn.execute("""
            CREATE TEMP TABLE package_events_temp AS 
            SELECT * FROM package_events
        """)
        
        # Store attachments if they exist
        print("Temporarily storing attachments...")
        conn.execute("""
            CREATE TEMP TABLE attachments_temp AS 
            SELECT * FROM attachments
        """)
        
        print("Dropping dependent tables...")
        conn.execute("DROP TABLE IF EXISTS attachments")
        conn.execute("DROP TABLE IF EXISTS package_events")
        conn.execute("DROP TABLE IF EXISTS packages")
        
        # Drop old recipients table
        print("Dropping old recipients table...")
        conn.execute("DROP TABLE recipients")
        
        # Rename new table
        print("Renaming new table...")
        conn.execute("ALTER TABLE recipients_new RENAME TO recipients")
        
        # Recreate indexes
        print("Recreating indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipients_employee_id ON recipients(employee_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipients_is_active ON recipients(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipients_name ON recipients(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipients_department ON recipients(department)")
        
        # Restore packages table
        print("Recreating packages table...")
        conn.execute("""
            CREATE TABLE packages (
                id UUID PRIMARY KEY,
                tracking_no VARCHAR NOT NULL,
                carrier VARCHAR NOT NULL,
                recipient_id UUID NOT NULL,
                status VARCHAR NOT NULL CHECK (status IN ('registered', 'awaiting_pickup', 'out_for_delivery', 'delivered', 'returned')),
                notes TEXT,
                created_by UUID NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (recipient_id) REFERENCES recipients(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        if package_count > 0:
            print("Restoring package data...")
            conn.execute("""
                INSERT INTO packages
                SELECT * FROM packages_temp
            """)
        
        print("Recreating package indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_tracking_no ON packages(tracking_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_recipient_id ON packages(recipient_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_status ON packages(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_created_at ON packages(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_created_by ON packages(created_by)")
        
        # Restore package_events table
        print("Recreating package_events table...")
        conn.execute("""
            CREATE TABLE package_events (
                id UUID PRIMARY KEY,
                package_id UUID NOT NULL,
                old_status VARCHAR,
                new_status VARCHAR NOT NULL,
                notes TEXT,
                actor_id UUID NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (package_id) REFERENCES packages(id),
                FOREIGN KEY (actor_id) REFERENCES users(id)
            )
        """)
        
        event_count = conn.execute("SELECT COUNT(*) FROM package_events_temp").fetchone()[0]
        if event_count > 0:
            print(f"Restoring {event_count} package events...")
            conn.execute("""
                INSERT INTO package_events
                SELECT * FROM package_events_temp
            """)
        
        print("Recreating package_events indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_package_id ON package_events(package_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_actor_id ON package_events(actor_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_created_at ON package_events(created_at)")
        
        # Restore attachments table
        print("Recreating attachments table...")
        conn.execute("""
            CREATE TABLE attachments (
                id UUID PRIMARY KEY,
                package_id UUID NOT NULL,
                filename VARCHAR NOT NULL,
                file_path VARCHAR NOT NULL,
                mime_type VARCHAR NOT NULL,
                file_size INTEGER NOT NULL,
                uploaded_by UUID NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (package_id) REFERENCES packages(id),
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        """)
        
        attachment_count = conn.execute("SELECT COUNT(*) FROM attachments_temp").fetchone()[0]
        if attachment_count > 0:
            print(f"Restoring {attachment_count} attachments...")
            conn.execute("""
                INSERT INTO attachments
                SELECT * FROM attachments_temp
            """)
        
        print("Recreating attachments indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_package_id ON attachments(package_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_uploaded_by ON attachments(uploaded_by)")
        
        conn.execute("COMMIT")
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        try:
            conn.execute("ROLLBACK")
        except:
            pass
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_email_unique_constraint.py <path_to_database>")
        print("Example: python add_email_unique_constraint.py ./data/mailroom.duckdb")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)
    
    success = migrate(db_path)
    sys.exit(0 if success else 1)
