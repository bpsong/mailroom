"""Backfill missing department data for existing recipients."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import get_db
from app.database.write_queue import get_write_queue


async def backfill_departments():
    """Backfill NULL departments with 'Unknown'."""
    print("=" * 70)
    print("Recipient Department Backfill Script")
    print("=" * 70)
    print()
    
    db = get_db()
    
    # Check for recipients with NULL department
    print("Checking for recipients with missing department...")
    with db.get_read_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM recipients WHERE department IS NULL"
        ).fetchone()
        
        null_count = result[0]
        
        if null_count == 0:
            print("✓ No recipients need backfilling")
            print()
            return
        
        print(f"Found {null_count} recipients with NULL department")
        print()
        
        # Show sample of affected recipients
        print("Sample of affected recipients:")
        sample = conn.execute(
            """
            SELECT id, employee_id, name, email
            FROM recipients
            WHERE department IS NULL
            LIMIT 5
            """
        ).fetchall()
        
        for row in sample:
            print(f"  - {row[1]}: {row[2]} ({row[3]})")
        
        if null_count > 5:
            print(f"  ... and {null_count - 5} more")
        print()
    
    # Confirm with user
    response = input(f"Update {null_count} recipients with department='Unknown'? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Aborted by user")
        return
    
    print()
    print("Updating recipients...")
    
    # Update NULL departments to 'Unknown'
    write_queue = await get_write_queue()
    await write_queue.execute(
        """
        UPDATE recipients
        SET department = 'Unknown', updated_at = CURRENT_TIMESTAMP
        WHERE department IS NULL
        """
    )
    
    print(f"✓ Updated {null_count} recipients with department='Unknown'")
    print()
    print("=" * 70)
    print("IMPORTANT: Please review these recipients and update with correct departments")
    print("=" * 70)
    print()
    print("You can update departments via:")
    print("  1. Admin interface: http://localhost:8000/admin/recipients")
    print("  2. CSV import: http://localhost:8000/admin/recipients/import")
    print()


async def verify_no_null_departments():
    """Verify no recipients have NULL departments."""
    db = get_db()
    
    with db.get_read_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM recipients WHERE department IS NULL"
        ).fetchone()
        
        null_count = result[0]
        
        if null_count == 0:
            print("✓ Verification passed: All recipients have departments")
            return True
        else:
            print(f"✗ Verification failed: {null_count} recipients still have NULL department")
            return False


async def main():
    """Main entry point."""
    try:
        await backfill_departments()
        print()
        print("Verifying changes...")
        await verify_no_null_departments()
        print()
        print("Backfill complete!")
        
    except Exception as e:
        print(f"Error during backfill: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
