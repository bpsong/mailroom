"""Verify system settings service with audit logging."""

import asyncio
from uuid import UUID
from app.services.system_settings_service import system_settings_service
from app.database.connection import get_db


async def verify():
    """Verify system settings service."""
    print("Verifying SystemSettingsService with audit logging...")
    
    # Get a real user ID from the database
    db = get_db()
    with db.get_read_connection() as conn:
        result = conn.execute("SELECT id FROM users WHERE role = 'super_admin' LIMIT 1").fetchone()
        if not result:
            print("Error: No super admin found in database.")
            return
        user_id = UUID(result[0]) if isinstance(result[0], str) else result[0]
    print(f"✓ Using super admin ID: {user_id}")
    
    # Test setting QR base URL
    test_url = "https://mailroom.company.local"
    print(f"\nSetting QR base URL to: {test_url}")
    await system_settings_service.set_qr_base_url(test_url, user_id)
    print("✓ QR base URL set successfully")
    
    # Wait for write queue
    await asyncio.sleep(1)
    
    # Verify it was saved
    saved_url = await system_settings_service.get_qr_base_url()
    print(f"✓ Retrieved QR base URL: {saved_url}")
    
    if saved_url == test_url:
        print("✅ System settings service working correctly!")
    else:
        print(f"❌ Mismatch: expected {test_url}, got {saved_url}")
    
    # Check audit log
    print("\nChecking audit log...")
    with db.get_read_connection() as conn:
        result = conn.execute("""
            SELECT event_type, details, created_at
            FROM auth_events
            WHERE event_type = 'system_settings_change'
            ORDER BY created_at DESC
            LIMIT 1
        """).fetchone()
        
        if result:
            print(f"✓ Audit log entry found:")
            print(f"  Event type: {result[0]}")
            print(f"  Details: {result[1]}")
            print(f"  Created at: {result[2]}")
            print("✅ Audit logging working correctly!")
        else:
            print("⚠️  No audit log entry found (may still be in write queue)")


if __name__ == "__main__":
    asyncio.run(verify())
