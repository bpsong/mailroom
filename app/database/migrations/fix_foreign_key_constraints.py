"""
Migration: Remove foreign key constraints from package_events and attachments.

DuckDB has limitations with foreign keys that cause issues with UPDATE operations.
This migration removes the FK constraints and relies on application-level integrity.
"""

from app.database.connection import get_db


def run_migration():
    """Run the migration to remove foreign key constraints."""
    db = get_db()
    
    with db.get_write_connection() as conn:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # Backup existing data
            print("Backing up existing data...")
            events_backup = conn.execute("SELECT * FROM package_events").fetchall()
            attachments_backup = conn.execute("SELECT * FROM attachments").fetchall()
            
            # Drop existing tables (in correct order due to dependencies)
            print("Dropping old tables...")
            conn.execute("DROP TABLE IF EXISTS attachments")
            conn.execute("DROP TABLE IF EXISTS package_events")
            
            # Recreate package_events WITHOUT foreign keys
            print("Creating package_events without FK constraints...")
            conn.execute("""
                CREATE TABLE package_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    package_id UUID NOT NULL,
                    old_status VARCHAR,
                    new_status VARCHAR NOT NULL,
                    notes TEXT,
                    actor_id UUID NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recreate attachments WITHOUT foreign keys
            print("Creating attachments without FK constraints...")
            conn.execute("""
                CREATE TABLE attachments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    package_id UUID NOT NULL,
                    filename VARCHAR NOT NULL,
                    file_path VARCHAR NOT NULL,
                    mime_type VARCHAR NOT NULL,
                    file_size INTEGER NOT NULL,
                    uploaded_by UUID NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Restore data
            print(f"Restoring {len(events_backup)} package events...")
            for row in events_backup:
                conn.execute(
                    "INSERT INTO package_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                    list(row)
                )
            
            print(f"Restoring {len(attachments_backup)} attachments...")
            for row in attachments_backup:
                conn.execute(
                    "INSERT INTO attachments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    list(row)
                )
            
            # Recreate indexes
            print("Creating indexes...")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_package_id ON package_events(package_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_actor_id ON package_events(actor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_created_at ON package_events(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_package_id ON attachments(package_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_uploaded_by ON attachments(uploaded_by)")
            
            # Commit transaction
            conn.commit()
            print("✓ Migration completed: Foreign key constraints removed")
            
        except Exception as e:
            conn.rollback()
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == "__main__":
    run_migration()
