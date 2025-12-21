"""System settings service for managing system-wide configuration."""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.database.connection import get_db
from app.database.write_queue import get_write_queue
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class SystemSettingsService:
    """Service for managing system-wide settings."""
    
    async def get_qr_base_url(self) -> Optional[str]:
        """
        Get configured QR code base URL.
        
        Returns None if not configured (will use request.base_url as fallback).
        """
        db = get_db()
        with db.get_read_connection() as conn:
            try:
                result = conn.execute(
                    "SELECT value FROM system_settings WHERE key = 'qr_base_url'",
                ).fetchone()
            except Exception as exc:
                # Table may not exist in freshly initialized test databases; fall back
                logger.debug("System settings table unavailable when reading qr_base_url: %s", exc)
                return None
            
            return result[0] if result else None
    
    async def set_qr_base_url(
        self,
        url: str,
        actor_id: UUID,
        actor_username: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Set QR code base URL (Super Admin only).
        
        Args:
            url: Base URL (e.g., 'https://mailroom.company.local')
            actor_id: Super Admin user ID
            actor_username: Username of actor for audit logging
            ip_address: Client IP for audit logging
            
        Raises:
            ValueError: If URL format is invalid
        """
        if not self.validate_base_url(url):
            raise ValueError("Invalid URL format. Must start with http:// or https://")
        
        # Get old value for audit log
        old_value = await self.get_qr_base_url()
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        query = """
            INSERT INTO system_settings (key, value, updated_by, updated_at)
            VALUES ('qr_base_url', ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_by = excluded.updated_by,
                updated_at = excluded.updated_at
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(
            query,
            [url, str(actor_id), datetime.utcnow()],
        )
        
        # Log to audit trail
        action = "qr_base_url_updated" if old_value else "qr_base_url_created"
        await audit_service.log_auth_event(
            event_type="system_settings_change",
            user_id=actor_id,
            username=actor_username,
            ip_address=ip_address,
            details={
                "action": action,
                "setting_key": "qr_base_url",
                "old_value": old_value,
                "new_value": url,
            }
        )
    
    def validate_base_url(self, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        return url.startswith('http://') or url.startswith('https://')


# Global instance
system_settings_service = SystemSettingsService()
