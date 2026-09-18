"""Authentication orchestration: login flow, lockout, and audit events.

Password hashing/policy lives in :mod:`app.services.password_policy` and
session persistence in :mod:`app.services.session_store`. This module keeps
the historic :class:`AuthService` API so routes, middleware, and tests are
unaffected: methods below delegate to those focused modules.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.clock import utc_now
from app.config import settings
from app.database.write_queue import get_write_queue
from app.models import Session, User
from app.services import password_policy, session_store

logger = logging.getLogger(__name__)


@dataclass
class AuthenticationError(Exception):
    """Structured authentication failure used by the service layer."""

    status_code: int
    detail: str
    reason: str
    locked_until: datetime | None = None


class AuthService:
    """Facade over password policy and session storage plus login orchestration."""

    # -- Password policy delegates (see app.services.password_policy) --

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return password_policy.hash_password(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash; corrupt hashes verify as False."""
        return password_policy.verify_password(password, password_hash)

    def validate_password_strength(self, password: str) -> tuple[bool, str | None]:
        """Validate password meets strength requirements."""
        return password_policy.validate_password_strength(password)

    def check_password_history(self, password: str, password_history: str | None) -> bool:
        """Check if password was used in recent history."""
        return password_policy.check_password_history(password, password_history)

    def update_password_history(self, current_hash: str, password_history: str | None) -> str:
        """Update password history with new hash."""
        return password_policy.update_password_history(current_hash, password_history)

    # -- Session store delegates (see app.services.session_store) --

    def generate_session_token(self) -> str:
        """Generate a secure random session token."""
        return session_store.generate_session_token()

    async def create_session(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new session for a user."""
        return await session_store.create_session(user_id, ip_address, user_agent)

    async def validate_session(self, token: str) -> tuple[Session, User] | None:
        """Validate a session token and return session and user if valid."""
        return await session_store.validate_session(token)

    async def renew_session(self, token: str) -> bool:
        """Renew a session by extending its expiration time."""
        return await session_store.renew_session(token)

    async def terminate_session(self, token: str) -> bool:
        """Terminate a session by deleting it from the database."""
        return await session_store.terminate_session(token)

    async def terminate_user_sessions(self, user_id: UUID) -> bool:
        """Terminate all sessions for a user."""
        return await session_store.terminate_user_sessions(user_id)

    async def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions; returns the number deleted."""
        return await session_store.cleanup_expired_sessions()

    async def get_user_sessions(self, user_id: UUID) -> list[Session]:
        """Get all active sessions for a user."""
        return await session_store.get_user_sessions(user_id)

    async def terminate_session_by_id(self, session_id: UUID, user_id: UUID) -> bool:
        """Terminate a specific session by ID (only if it belongs to the user)."""
        return await session_store.terminate_session_by_id(session_id, user_id)

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str | None = None,
    ) -> User:
        """
        Authenticate a user by username and password.

        Args:
            username: Username provided by the client
            password: Plain text password provided by the client
            ip_address: Client IP address for audit logging

        Returns:
            Authenticated user object

        Raises:
            AuthenticationError: If authentication fails for any reason
        """
        from app.database.connection import get_db

        is_locked, locked_until = await self.check_account_lockout(username)
        if is_locked:
            await self.log_auth_event(
                event_type="login_failed",
                username=username,
                ip_address=ip_address,
                details=json.dumps({"reason": "account_locked", "locked_until": str(locked_until)}),
            )
            raise AuthenticationError(
                status_code=403,
                detail=f"Account is locked until {locked_until}. Please try again later.",
                reason="account_locked",
                locked_until=locked_until,
            )

        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, username, password_hash, full_name, role, is_active,
                       must_change_password, password_history, failed_login_count,
                       locked_until, created_at, updated_at
                FROM users
                WHERE username = ?
                """,
                [username],
            ).fetchone()

        if not result:
            await self.log_auth_event(
                event_type="login_failed",
                username=username,
                ip_address=ip_address,
                details=json.dumps({"reason": "invalid_username"}),
            )
            raise AuthenticationError(
                status_code=401,
                detail="Invalid username or password",
                reason="invalid_username",
            )

        user = User(
            id=result[0],
            username=result[1],
            password_hash=result[2],
            full_name=result[3],
            role=result[4],
            is_active=result[5],
            must_change_password=result[6],
            password_history=result[7],
            failed_login_count=result[8],
            locked_until=result[9],
            created_at=result[10],
            updated_at=result[11],
        )

        if not user.is_active:
            logger.debug("Inactive user '%s' attempted login", username)
            await self.log_auth_event(
                event_type="login_failed",
                username=username,
                ip_address=ip_address,
                details=json.dumps({"reason": "account_inactive"}),
            )
            raise AuthenticationError(
                status_code=403,
                detail="Account is inactive. Please contact an administrator.",
                reason="account_inactive",
            )

        if not self.verify_password(password, user.password_hash):
            logger.debug("Invalid password for user '%s'", username)
            await self.increment_failed_login(username)
            await self.log_auth_event(
                event_type="login_failed",
                username=username,
                ip_address=ip_address,
                details=json.dumps({"reason": "invalid_password"}),
            )
            raise AuthenticationError(
                status_code=401,
                detail="Invalid username or password",
                reason="invalid_password",
            )

        await self.reset_failed_login(username)
        return user
    
    async def check_account_lockout(self, username: str) -> tuple[bool, datetime | None]:
        """
        Check if an account is locked due to failed login attempts.
        
        Args:
            username: Username to check
            
        Returns:
            Tuple of (is_locked, locked_until)
        """
        from app.database.connection import get_db
        
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT locked_until, failed_login_count
                FROM users
                WHERE username = ?
                """,
                [username],
            ).fetchone()
            
            if not result:
                return False, None
            
            locked_until, failed_count = result
            
            # Check if account is currently locked
            if locked_until and locked_until > utc_now():
                return True, locked_until
            
            return False, None
    
    async def increment_failed_login(self, username: str) -> None:
        """
        Increment failed login counter and lock account if threshold exceeded.
        
        Args:
            username: Username that failed login
        """
        # Check current failed count
        from app.database.connection import get_db
        
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                "SELECT failed_login_count FROM users WHERE username = ?",
                [username],
            ).fetchone()
            
            if not result:
                return
            
            failed_count = result[0] + 1
        
        # Lock account if threshold exceeded
        write_queue = await get_write_queue()
        if failed_count >= settings.max_failed_logins:
            locked_until = utc_now() + timedelta(
                seconds=settings.account_lockout_duration
            )
            query = """
                UPDATE users
                SET failed_login_count = ?, locked_until = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            """
            await write_queue.execute(query, [failed_count, locked_until, username])
        else:
            query = """
                UPDATE users
                SET failed_login_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            """
            await write_queue.execute(query, [failed_count, username])
    
    async def reset_failed_login(self, username: str) -> None:
        """
        Reset failed login counter after successful login.
        
        Args:
            username: Username that successfully logged in
        """
        query = """
            UPDATE users
            SET failed_login_count = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
        """
        write_queue = await get_write_queue()
        await write_queue.execute(query, [username])
    
    async def log_auth_event(
        self,
        event_type: str,
        user_id: UUID | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        details: str | None = None,
    ) -> None:
        """
        Log an authentication event to the audit log.
        
        Args:
            event_type: Type of event (login, login_failed, logout, etc.)
            user_id: ID of the user (if applicable)
            username: Username (for failed logins)
            ip_address: IP address of the client
            details: Additional details as JSON string
        """
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
                details,
            ],
        )


# Global auth service instance
auth_service = AuthService()
