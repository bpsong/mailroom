"""Session lifecycle storage: tokens, validation, renewal, termination."""

import logging
import secrets
import sqlite3
from datetime import timedelta
from uuid import UUID

from app.clock import utc_now
from app.config import settings
from app.database.write_queue import get_write_queue
from app.models import Session, SessionCreate, User

logger = logging.getLogger(__name__)

def generate_session_token() -> str:
    """
    Generate a secure random session token.

    Returns:
        Secure random token string
    """
    return secrets.token_urlsafe(32)


async def create_session(user_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
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
    logger.debug(
        "Preparing to create session for user_id=%s active_sessions=%s max_sessions=%s",
        user_id,
        len(result),
        max_sessions,
    )

    if len(result) >= max_sessions:
        # Delete oldest sessions to make room
        sessions_to_delete = len(result) - max_sessions + 1
        oldest_session_ids = [row[0] for row in result[:sessions_to_delete]]

        write_queue = await get_write_queue()
        logger.debug(
            "Session cap exceeded for user_id=%s; deleting %s oldest sessions; queue_depth_before_delete=%s",
            user_id,
            len(oldest_session_ids),
            write_queue.queue.qsize(),
        )
        for session_id in oldest_session_ids:
            await write_queue.execute(
                "DELETE FROM sessions WHERE id = ?",
                [session_id],
            )

    # Generate new session
    token = generate_session_token()
    expires_at = utc_now() + timedelta(seconds=settings.session_timeout)
    logger.debug(
        "Generated session token for user_id=%s token_prefix=%s expires_at=%s",
        user_id,
        token[:8],
        expires_at,
    )

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
    logger.debug(
        "Enqueuing session insert for user_id=%s token_prefix=%s queue_depth_before_insert=%s",
        user_id,
        token[:8],
        write_queue.queue.qsize(),
    )
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
    logger.debug(
        "Session insert completed for user_id=%s session_id=%s token_prefix=%s queue_depth_after_insert=%s",
        user_id,
        row[0],
        token[:8],
        write_queue.queue.qsize(),
    )
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
    except sqlite3.Error as exc:
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


async def validate_session(token: str) -> tuple[Session, User] | None:
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


async def renew_session(token: str) -> bool:
    """
    Renew a session by extending its expiration time.

    Args:
        token: Session token to renew

    Returns:
        True if renewed successfully, False otherwise
    """
    new_expires_at = utc_now() + timedelta(seconds=settings.session_timeout)

    query = """
        UPDATE sessions
        SET expires_at = ?, last_activity = CURRENT_TIMESTAMP
        WHERE token = ? AND expires_at > CURRENT_TIMESTAMP
    """

    try:
        write_queue = await get_write_queue()
        await write_queue.execute(query, [new_expires_at, token])
        return True
    except (sqlite3.Error, TimeoutError):
        return False


async def terminate_session(token: str) -> bool:
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
    except (sqlite3.Error, TimeoutError):
        return False


async def terminate_user_sessions(user_id: UUID) -> bool:
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
    except (sqlite3.Error, TimeoutError):
        return False


async def cleanup_expired_sessions() -> int:
    """
    Clean up all expired sessions from the database.

    This should be called on application startup and periodically
    to remove stale session data.

    Returns:
        Number of sessions deleted
    """
    from app.database.connection import get_db

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
    except (sqlite3.Error, TimeoutError):
        return 0


async def get_user_sessions(user_id: UUID) -> list[Session]:
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


async def terminate_session_by_id(session_id: UUID, user_id: UUID) -> bool:
    """
    Terminate a specific session by ID (only if it belongs to the user).

    Args:
        session_id: ID of the session to terminate
        user_id: ID of the user (for ownership verification)

    Returns:
        True if terminated successfully, False otherwise
    """
    query = "DELETE FROM sessions WHERE id = ? AND user_id = ? RETURNING id"

    try:
        write_queue = await get_write_queue()
        deleted = await write_queue.execute(
            query, [str(session_id), str(user_id)], return_result=True
        )
        return bool(deleted)
    except (sqlite3.Error, TimeoutError):
        return False
