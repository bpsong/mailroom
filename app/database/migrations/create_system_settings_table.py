"""Create system_settings table for storing system-wide configuration."""

import duckdb
import sys
from pathlib import Path


def run_migration():
    """Create system_settings table."""
    # Get database path
    db_path = Path("data/mailroom.duckdb")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = duckdb.connect(str(db_path))
        
        # Create system_settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_by UUID REFERENCES users(id),
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        print("✓ Created system_settings table")
        
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
