"""Health check service for monitoring system status."""

import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from app.config import settings
from app.services.database_service import get_database_service

logger = logging.getLogger(__name__)

# Track application start time
_app_start_time = time.time()


class HealthService:
    """
    Service for checking system health status.
    
    Provides health checks for:
    - Database connectivity
    - Disk space availability
    - Application uptime
    """
    
    def __init__(self):
        """Initialize the health service."""
        self.db_service = get_database_service()
    
    async def check_database(self) -> Dict[str, Any]:
        """
        Check database connection health.
        
        Returns:
            Dictionary with database health status
        """
        try:
            is_connected = await self.db_service.check_connection()
            
            if is_connected:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "connected": True
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Database connection failed",
                    "connected": False
                }
        
        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
                "connected": False
            }
    
    def check_disk_space(self) -> Dict[str, Any]:
        """
        Check available disk space for critical directories.
        
        Returns:
            Dictionary with disk space information
        """
        try:
            # Check disk space for database directory
            db_path = Path(settings.database_path).parent
            db_usage = shutil.disk_usage(db_path)
            
            # Check disk space for uploads directory
            upload_path = Path(settings.upload_dir)
            upload_usage = shutil.disk_usage(upload_path)
            
            # Calculate percentages
            db_percent_used = (db_usage.used / db_usage.total) * 100
            upload_percent_used = (upload_usage.used / upload_usage.total) * 100
            
            # Determine health status (warn if > 90% used)
            is_healthy = db_percent_used < 90 and upload_percent_used < 90
            
            return {
                "status": "healthy" if is_healthy else "warning",
                "database_directory": {
                    "path": str(db_path),
                    "total_gb": round(db_usage.total / (1024**3), 2),
                    "used_gb": round(db_usage.used / (1024**3), 2),
                    "free_gb": round(db_usage.free / (1024**3), 2),
                    "percent_used": round(db_percent_used, 2)
                },
                "upload_directory": {
                    "path": str(upload_path),
                    "total_gb": round(upload_usage.total / (1024**3), 2),
                    "used_gb": round(upload_usage.used / (1024**3), 2),
                    "free_gb": round(upload_usage.free / (1024**3), 2),
                    "percent_used": round(upload_percent_used, 2)
                }
            }
        
        except Exception as e:
            logger.error(f"Disk space check error: {e}")
            return {
                "status": "error",
                "message": f"Failed to check disk space: {str(e)}"
            }
    
    def get_uptime(self) -> Dict[str, Any]:
        """
        Get application uptime information.
        
        Returns:
            Dictionary with uptime information
        """
        try:
            current_time = time.time()
            uptime_seconds = current_time - _app_start_time
            
            # Convert to human-readable format
            uptime_delta = timedelta(seconds=int(uptime_seconds))
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return {
                "status": "healthy",
                "started_at": datetime.fromtimestamp(_app_start_time).isoformat(),
                "uptime_seconds": int(uptime_seconds),
                "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s"
            }
        
        except Exception as e:
            logger.error(f"Uptime check error: {e}")
            return {
                "status": "error",
                "message": f"Failed to get uptime: {str(e)}"
            }
    
    async def get_full_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all system components.
        
        Returns:
            Dictionary with complete health status
        """
        # Check all components
        database_health = await self.check_database()
        disk_health = self.check_disk_space()
        uptime_info = self.get_uptime()
        
        # Determine overall status
        all_healthy = (
            database_health["status"] == "healthy" and
            disk_health["status"] in ["healthy", "warning"] and
            uptime_info["status"] == "healthy"
        )
        
        overall_status = "healthy" if all_healthy else "unhealthy"
        
        # If database is down, mark as unhealthy regardless of other checks
        if not database_health.get("connected", False):
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {
                "database": database_health,
                "disk_space": disk_health,
                "uptime": uptime_info
            }
        }


# Global health service instance
_health_service: HealthService | None = None


def get_health_service() -> HealthService:
    """
    Get the global health service instance.
    
    Returns:
        HealthService instance
    """
    global _health_service
    
    if _health_service is None:
        _health_service = HealthService()
    
    return _health_service
