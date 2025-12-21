"""Authentication service for password hashing and validation."""

import json
import re
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.database.write_queue import get_write_queue
from app.models import User, Session, SessionCreate, AuthEvent, AuthEventCreate

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations including password hashing and session management."""
    
    def __init__(self):
        """Initialize the authentication service with Argon2 hasher."""
        self.hasher = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        )
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using Argon2id.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        return self.hasher.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            self.hasher.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
    
    def validate_password_strength(self, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password meets strength requirements.
        
        Requirements:
        - At least 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < settings.password_min_length:
            return False, f"Password must be at least {settings.password_min_length} characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        
        return True, None
    
    def check_password_history(self, password: str, password_history: Optional[str]) -> bool:
        """
        Check if password was used in recent history.
        
        Args:
            password: Plain text password to check
            password_history: JSON string of previous password hashes
            
        Returns:
            True if password is in history (should be rejected), False otherwise
        """
        if not password_history:
            return False
        
        try:
            history = json.loads(password_history)
            if not isinstance(history, list):
                return False
            
            # Check against last N passwords
            for old_hash in history[-settings.password_history_count:]:
                if self.verify_password(password, old_hash):
                    return True
            
            return False
        except (json.JSONDecodeError, Exception):
            return False
    
    def update_password_history(
        self, 
        current_hash: str, 
        password_history: Optional[str]
    ) -> str:
        """
        Update password history with new hash.
        
        Args:
            current_hash: New password hash to add
            password_history: Existing password history JSON string
            
        Returns:
            Updated password history JSON string
        """
        try:
            if password_history:
                history = json.loads(password_history)
                if not isinstance(history, list):
                    history = []
            else:
                history = []
        except json.JSONDecodeError:
            history = []
        
        # Add current hash to history
        history.append(current_hash)
        
        # Keep only the last N+1 passwords (current + history)
        history = history[-(settings.password_history_count + 1):]
        
        return json.dumps(history)
    
    def generate_session_token(self) -> str:
        """
        Generate a secure random session token.
        
        Returns:
            Secure random token string
        """
        return secrets.token_urlsafe(32)
    
    async def create_session(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        """
        Create a new session for a user.
        
        Enforces maximum concurrent sessions per user (default: 3).
        If limit is exceeded, oldest sessions are terminated.
        
        Args:
            user_id: ID of the user
            ip_address: IP address of the client
            user_agent: User agent string of the client
            
        Returns:
            Created session object
        """
        from app.database.connection import get_db
        
        # Check current active session count
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, created_at
                FROM sessions
                WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
                ORDER BY created_at ASC
                """,
                [str(user_id)],
            ).fetchall()
        
        # Enforce max concurrent sessions (configurable, default 3)
        max_sessions = getattr(settings, 'max_concurrent_sessions', 3)
        
        if len(result) >= max_sessions:
            # Delete oldest sessions to make room
            sessions_to_delete = len(result) - max_sessions + 1
            oldest_session_ids = [row[0] for row in result[:sessions_to_delete]]
            
            write_queue = await get_write_queue()
            for session_id in oldest_session_ids:
                await write_queue.execute(
                    "DELETE FROM sessions WHERE id = ?",
                    [session_id],
                )
        
        # Generate new session
        token = self.generate_session_token()
        expires_at = datetime.now() + timedelta(seconds=settings.session_timeout)
        
        session_data = SessionCreate(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Insert session into database
        query = """
            INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id, user_id, token, expires_at, last_activity, ip_address, user_agent, created_at
        """
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [
                str(session_data.user_id),
                session_data.token,
                session_data.expires_at,
                session_data.ip_address,
                session_data.user_agent,
            ],
            return_result=True,
        )
        
        row = result[0]
        # Verify session is immediately visible to read connections
        try:
            with db.get_read_connection() as conn:
                visibility = conn.execute(
                    "SELECT 1 FROM sessions WHERE token = ?",
                    [token],
                ).fetchone()
                logger.debug(
                    "Post-insert visibility for session token_prefix=%s exists=%s",
                    token[:8],
                    bool(visibility),
                )
        except Exception as exc:
            logger.warning(
                "Session visibility check failed for token_prefix=%s: %s",
                token[:8],
                exc,
            )
        
        return Session(
            id=row[0],
            user_id=row[1],
            token=row[2],
            expires_at=row[3],
            last_activity=row[4],
            ip_address=row[5],
            user_agent=row[6],
            created_at=row[7],
        )
    
    async def validate_session(self, token: str) -> Optional[tuple[Session, User]]:
        """
        Validate a session token and return session and user if valid.
        
        Args:
            token: Session token to validate
            
        Returns:
            Tuple of (Session, User) if valid, None otherwise
        """
        from app.database.connection import get_db
        
        db = get_db()
        with db.get_read_connection() as conn:
            # Get session with user data
            result = conn.execute(
                """
                SELECT 
                    s.id, s.user_id, s.token, s.expires_at, s.last_activity,
                    s.ip_address, s.user_agent, s.created_at,
                    u.id, u.username, u.password_hash, u.full_name, u.role,
                    u.is_active, u.must_change_password, u.password_history,
                    u.failed_login_count, u.locked_until, u.created_at, u.updated_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
                """,
                [token],
            ).fetchone()
            
            if not result:
                logger.debug("Session token not found/expired token_prefix=%s", token[:8])
                return None
            
            # Parse session
            session = Session(
                id=result[0],
                user_id=result[1],
                token=result[2],
                expires_at=result[3],
                last_activity=result[4],
                ip_address=result[5],
                user_agent=result[6],
                created_at=result[7],
            )
            
            # Parse user
            user = User(
                id=result[8],
                username=result[9],
                password_hash=result[10],
                full_name=result[11],
                role=result[12],
                is_active=result[13],
                must_change_password=result[14],
                password_history=result[15],
                failed_login_count=result[16],
                locked_until=result[17],
                created_at=result[18],
                updated_at=result[19],
            )
            
            # Check if user is active
            if not user.is_active:
                return None
            
            logger.debug(
                "Validated session token token_prefix=%s for user '%s'",
                token[:8],
                user.username,
            )
            return session, user
    
    async def renew_session(self, token: str) -> bool:
        """
        Renew a session by extending its expiration time.
        
        Args:
            token: Session token to renew
            
        Returns:
            True if renewed successfully, False otherwise
        """
        new_expires_at = datetime.now() + timedelta(seconds=settings.session_timeout)
        
        query = """
            UPDATE sessions
            SET expires_at = ?, last_activity = CURRENT_TIMESTAMP
            WHERE token = ? AND expires_at > CURRENT_TIMESTAMP
        """
        
        try:
            write_queue = await get_write_queue()
            await write_queue.execute(query, [new_expires_at, token])
            return True
        except Exception:
            return False
    
    async def terminate_session(self, token: str) -> bool:
        """
        Terminate a session by deleting it from the database.
        
        Args:
            token: Session token to terminate
            
        Returns:
            True if terminated successfully, False otherwise
        """
        query = "DELETE FROM sessions WHERE token = ?"
        
        try:
            write_queue = await get_write_queue()
            await write_queue.execute(query, [token])
            return True
        except Exception:
            return False
    
    async def terminate_user_sessions(self, user_id: UUID) -> bool:
        """
        Terminate all sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if terminated successfully, False otherwise
        """
        query = "DELETE FROM sessions WHERE user_id = ?"
        
        try:
            write_queue = await get_write_queue()
            await write_queue.execute(query, [str(user_id)])
            return True
        except Exception:
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions from the database.
        
        This should be called on application startup and periodically
        to remove stale session data.
        
        Returns:
            Number of sessions deleted
        """
        query = "DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP"
        
        try:
            db = get_db()
            with db.get_read_connection() as conn:
                # First count how many will be deleted
                count_result = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE expires_at < CURRENT_TIMESTAMP"
                ).fetchone()
                count = count_result[0] if count_result else 0
            
            if count > 0:
                write_queue = await get_write_queue()
                await write_queue.execute(query, [])
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count
        except Exception:
            return False
    
    async def get_user_sessions(self, user_id: UUID) -> list[Session]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of active sessions
        """
        from app.database.connection import get_db
        
        db = get_db()
        with db.get_read_connection() as conn:
            results = conn.execute(
                """
                SELECT id, user_id, token, created_at, expires_at, last_activity,
                       ip_address, user_agent
                FROM sessions
                WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
                ORDER BY last_activity DESC
                """,
                [str(user_id)],
            ).fetchall()
        
        sessions = []
        for row in results:
            sessions.append(
                Session(
                    id=row[0],
                    user_id=row[1],
                    token=row[2],
                    created_at=row[3],
                    expires_at=row[4],
                    last_activity=row[5],
                    ip_address=row[6],
                    user_agent=row[7],
                )
            )
        
        return sessions
    
    async def terminate_session_by_id(self, session_id: UUID, user_id: UUID) -> bool:
        """
        Terminate a specific session by ID (only if it belongs to the user).
        
        Args:
            session_id: ID of the session to terminate
            user_id: ID of the user (for ownership verification)
            
        Returns:
            True if terminated successfully, False otherwise
        """
        query = "DELETE FROM sessions WHERE id = ? AND user_id = ?"
        
        try:
            write_queue = await get_write_queue()
            await write_queue.execute(query, [str(session_id), str(user_id)])
            return True
        except Exception:
            return False
    
    async def check_account_lockout(self, username: str) -> tuple[bool, Optional[datetime]]:
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
            if locked_until and locked_until > datetime.now():
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
            locked_until = datetime.now() + timedelta(
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
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None,
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
