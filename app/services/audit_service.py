"""Audit logging service for tracking system events and maintaining audit trails."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID
from logging.handlers import TimedRotatingFileHandler

from app.config import settings
from app.database.write_queue import get_write_queue
from app.database.connection import get_db


class AuditService:
    """Service for comprehensive audit logging of system events."""
    
    def __init__(self):
        """Initialize the audit service with file logger."""
        self._setup_file_logger()
    
    def _setup_file_logger(self) -> None:
        """Set up rotating file handler for system audit logs."""
        # Create logs directory if it doesn't exist
        log_dir = Path(settings.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create rotating file handler (weekly rotation)
        handler = TimedRotatingFileHandler(
            filename=settings.log_file,
            when='W0',  # Rotate on Monday
            interval=1,
            backupCount=52,  # Keep 52 weeks (1 year) of logs
            encoding='utf-8'
        )
        
        # Set format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    async def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an authentication event to both database and file.
        
        Args:
            event_type: Type of event (login, login_failed, logout, password_change, etc.)
            user_id: ID of the user (if applicable)
            username: Username (for failed logins or when user_id not available)
            ip_address: IP address of the client
            details: Additional details as dictionary
        """
        # Convert details to JSON string
        details_json = json.dumps(details) if details else None
        
        # Log to database
        query = """
            INSERT INTO auth_events (user_id, event_type, username, ip_address, details)
            VALUES (?, ?, ?, ?, ?)
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(
            query,
            [
                str(user_id) if user_id else None,
                event_type,
                username,
                ip_address,
                details_json,
            ],
        )
        
        # Log to file
        log_message = f"AUTH_EVENT: {event_type}"
        if user_id:
            log_message += f" | user_id={user_id}"
        if username:
            log_message += f" | username={username}"
        if ip_address:
            log_message += f" | ip={ip_address}"
        if details:
            log_message += f" | details={json.dumps(details)}"
        
        self.logger.info(log_message)
    
    async def log_user_management(
        self,
        action: str,
        actor_id: UUID,
        target_user_id: Optional[UUID] = None,
        target_username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log user management actions (create, edit, deactivate, password reset).
        
        Args:
            action: Action performed (user_created, user_edited, user_deactivated, password_reset)
            actor_id: ID of the user performing the action
            target_user_id: ID of the user being managed
            target_username: Username of the user being managed
            details: Additional details (e.g., changed fields, new role)
        """
        event_details = {
            'action': action,
            'actor_id': str(actor_id),
            'target_user_id': str(target_user_id) if target_user_id else None,
            'target_username': target_username,
            **(details or {})
        }
        
        await self.log_auth_event(
            event_type='user_management',
            user_id=actor_id,
            details=event_details,
        )
    
    async def log_recipient_import(
        self,
        actor_id: UUID,
        filename: str,
        records_created: int,
        records_updated: int,
        errors: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log recipient CSV import operations.
        
        Args:
            actor_id: ID of the user performing the import
            filename: Name of the imported CSV file
            records_created: Number of new recipients created
            records_updated: Number of existing recipients updated
            errors: Number of errors encountered
            details: Additional details (e.g., error messages)
        """
        import_details = {
            'action': 'recipient_import',
            'filename': filename,
            'records_created': records_created,
            'records_updated': records_updated,
            'errors': errors,
            **(details or {})
        }
        
        await self.log_auth_event(
            event_type='recipient_import',
            user_id=actor_id,
            details=import_details,
        )
        
        # Also log to file
        log_message = (
            f"RECIPIENT_IMPORT: user_id={actor_id} | filename={filename} | "
            f"created={records_created} | updated={records_updated} | errors={errors}"
        )
        self.logger.info(log_message)
    
    async def log_package_event(
        self,
        package_id: UUID,
        old_status: Optional[str],
        new_status: str,
        actor_id: UUID,
        notes: Optional[str] = None,
    ) -> None:
        """
        Log package status change events.
        
        Note: This is already handled by package_events table, but we also log to file.
        
        Args:
            package_id: ID of the package
            old_status: Previous status (None for new packages)
            new_status: New status
            actor_id: ID of the user making the change
            notes: Optional notes about the change
        """
        # The database insert is handled by PackageService
        # We just log to file here
        log_message = (
            f"PACKAGE_EVENT: package_id={package_id} | "
            f"status_change={old_status or 'NEW'}->{new_status} | "
            f"actor_id={actor_id}"
        )
        if notes:
            log_message += f" | notes={notes}"
        
        self.logger.info(log_message)
    
    async def get_auth_events(
        self,
        user_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        username: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Retrieve authentication events with filtering and pagination.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            username: Filter by username (partial match)
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (events list, total count)
        """
        db = get_db()
        
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if user_id:
            where_clauses.append("ae.user_id = ?")
            params.append(str(user_id))
        
        if event_type:
            where_clauses.append("ae.event_type = ?")
            params.append(event_type)
        
        if username:
            where_clauses.append("ae.username LIKE ?")
            params.append(f"%{username}%")
        
        if start_date:
            where_clauses.append("ae.created_at >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("ae.created_at <= ?")
            params.append(end_date)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        with db.get_read_connection() as conn:
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM auth_events ae WHERE {where_sql}",
                params,
            ).fetchone()
            total_count = count_result[0] if count_result else 0
            
            # Get events
            query = f"""
                SELECT 
                    ae.id, ae.user_id, ae.event_type, ae.username, 
                    ae.ip_address, ae.details, ae.created_at,
                    u.full_name, u.role
                FROM auth_events ae
                LEFT JOIN users u ON ae.user_id = u.id
                WHERE {where_sql}
                ORDER BY ae.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            results = conn.execute(
                query,
                params + [limit, offset],
            ).fetchall()
            
            events = []
            for row in results:
                event = {
                    'id': str(row[0]),
                    'user_id': str(row[1]) if row[1] else None,
                    'event_type': row[2],
                    'username': row[3],
                    'ip_address': row[4],
                    'details': json.loads(row[5]) if row[5] else None,
                    'created_at': row[6],
                    'user_full_name': row[7],
                    'user_role': row[8],
                }
                events.append(event)
            
            return events, total_count
    
    async def cleanup_old_logs(self, retention_days: int = 365) -> int:
        """
        Clean up audit logs older than retention period.
        
        Args:
            retention_days: Number of days to retain logs (default 365)
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        query = "DELETE FROM auth_events WHERE created_at < ?"
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [cutoff_date],
            return_result=True,
        )
        
        # Log the cleanup
        self.logger.info(
            f"AUDIT_CLEANUP: Deleted auth_events older than {cutoff_date.date()}"
        )
        
        return 0  # DuckDB doesn't return affected rows easily
    
    def get_log_file_path(self) -> Path:
        """
        Get the path to the current audit log file.
        
        Returns:
            Path to the log file
        """
        return Path(settings.log_file)


# Global audit service instance
audit_service = AuditService()
