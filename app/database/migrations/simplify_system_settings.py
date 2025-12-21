"""Simplify system_settings table - remove foreign key constraint."""

import duckdb
import sys
from pathlib import Path


def run_migration():
    """Recreate system_settings table without foreign key."""
    # Get database path
    db_path = Path("data/mailroom.duckdb")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = duckdb.connect(str(db_path))
        
        # Drop existing table
        conn.execute("DROP TABLE IF EXISTS system_settings")
        print("✓ Dropped existing system_settings table")
        
        # Recreate without foreign key - just store UUID as text for audit trail
        conn.execute("""
            CREATE TABLE system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_by TEXT,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        print("✓ Created simplified system_settings table")
        print("  - No foreign key constraint")
        print("  - updated_by is just a text field for audit trail")
        
        conn.close()
        print("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
