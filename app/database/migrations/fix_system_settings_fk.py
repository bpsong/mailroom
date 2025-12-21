"""Fix system_settings table to make updated_by nullable."""

import duckdb
import sys
from pathlib import Path


def run_migration():
    """Recreate system_settings table with nullable updated_by."""
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
        
        # Recreate with nullable updated_by
        conn.execute("""
            CREATE TABLE system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_by UUID,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        print("✓ Created system_settings table with nullable updated_by")
        
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
