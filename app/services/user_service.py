"""User management service for CRUD operations."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.models import User, UserCreate, UserPublic
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
from app.database.connection import get_db
from app.database.write_queue import get_write_queue


class UserService:
    """Service for user management operations."""
    
    async def create_user(
        self,
        user_data: UserCreate,
        actor: User,
    ) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            actor: User performing the action
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If username already exists or validation fails
            PermissionError: If actor doesn't have permission
        """
        # Validate password strength
        is_valid, error_msg = auth_service.validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Check if username already exists
        if await self._username_exists(user_data.username):
            raise ValueError(f"Username '{user_data.username}' already exists")
        
        # Hash password
        password_hash = auth_service.hash_password(user_data.password)
        
        # Initialize password history with first hash
        password_history = json.dumps([password_hash])
        
        # Insert user into database
        query = """
            INSERT INTO users (username, password_hash, full_name, role, password_history, must_change_password)
            VALUES (?, ?, ?, ?, ?, true)
            RETURNING id, username, password_hash, full_name, role, is_active,
                      must_change_password, password_history, failed_login_count,
                      locked_until, created_at, updated_at
        """
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [
                user_data.username,
                password_hash,
                user_data.full_name,
                user_data.role,
                password_history,
            ],
            return_result=True,
        )
        
        row = result[0]
        user = User(
            id=row[0],
            username=row[1],
            password_hash=row[2],
            full_name=row[3],
            role=row[4],
            is_active=row[5],
            must_change_password=row[6],
            password_history=row[7],
            failed_login_count=row[8],
            locked_until=row[9],
            created_at=row[10],
            updated_at=row[11],
        )
        
        # Log user creation event
        await audit_service.log_user_management(
            action="user_created",
            actor_id=actor.id,
            target_user_id=user.id,
            target_username=user.username,
            details={"role": user.role},
        )
        
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID to retrieve
            
        Returns:
            User object if found, None otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, username, password_hash, full_name, role, is_active,
                       must_change_password, password_history, failed_login_count,
                       locked_until, created_at, updated_at
                FROM users
                WHERE id = ?
                """,
                [str(user_id)],
            ).fetchone()
            
            if not result:
                return None
            
            return User(
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
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: Username to retrieve
            
        Returns:
            User object if found, None otherwise
        """
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
                return None
            
            return User(
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
    
    async def update_user(
        self,
        user_id: UUID,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        actor: Optional[User] = None,
    ) -> User:
        """
        Update user information.
        
        Args:
            user_id: ID of user to update
            full_name: New full name (optional)
            role: New role (optional)
            actor: User performing the action
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If user not found or validation fails
        """
        # Get current user
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)
        
        if role is not None:
            if role not in ["super_admin", "admin", "operator"]:
                raise ValueError("Invalid role")
            updates.append("role = ?")
            params.append(role)
        
        if not updates:
            return user  # No changes
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(str(user_id))
        
        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ?
            RETURNING id, username, password_hash, full_name, role, is_active,
                      must_change_password, password_history, failed_login_count,
                      locked_until, created_at, updated_at
        """
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(query, params, return_result=True)
        
        row = result[0]
        updated_user = User(
            id=row[0],
            username=row[1],
            password_hash=row[2],
            full_name=row[3],
            role=row[4],
            is_active=row[5],
            must_change_password=row[6],
            password_history=row[7],
            failed_login_count=row[8],
            locked_until=row[9],
            created_at=row[10],
            updated_at=row[11],
        )
        
        # Log user update event
        if actor:
            await audit_service.log_user_management(
                action="user_updated",
                actor_id=actor.id,
                target_user_id=user_id,
                target_username=updated_user.username,
                details={
                    "full_name": full_name,
                    "role": role,
                },
            )
        
        return updated_user
    
    async def deactivate_user(
        self,
        user_id: UUID,
        actor: User,
    ) -> None:
        """
        Deactivate a user (soft delete) and terminate all their sessions.
        
        Args:
            user_id: ID of user to deactivate
            actor: User performing the action
            
        Raises:
            ValueError: If user not found
        """
        # Get user to verify it exists
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Deactivate user
        query = """
            UPDATE users
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(query, [str(user_id)])
        
        # Terminate all user sessions
        await auth_service.terminate_user_sessions(user_id)
        
        # Log deactivation event
        await audit_service.log_user_management(
            action="user_deactivated",
            actor_id=actor.id,
            target_user_id=user_id,
            target_username=user.username,
        )
    
    async def reset_user_password(
        self,
        user_id: UUID,
        new_password: str,
        force_change: bool = True,
        actor: Optional[User] = None,
    ) -> None:
        """
        Reset a user's password (admin action).
        
        Args:
            user_id: ID of user whose password to reset
            new_password: New password
            force_change: Whether to require password change on next login
            actor: User performing the action
            
        Raises:
            ValueError: If user not found or password validation fails
        """
        # Get user
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Validate password strength
        is_valid, error_msg = auth_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Check password history
        if auth_service.check_password_history(new_password, user.password_history):
            raise ValueError(
                f"Password was used recently. Please choose a different password."
            )
        
        # Hash new password
        new_hash = auth_service.hash_password(new_password)
        
        # Update password history
        new_history = auth_service.update_password_history(new_hash, user.password_history)
        
        # Update password in database
        query = """
            UPDATE users
            SET password_hash = ?,
                password_history = ?,
                must_change_password = ?,
                failed_login_count = 0,
                locked_until = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(
            query,
            [new_hash, new_history, force_change, str(user_id)],
        )
        
        # Terminate all user sessions
        await auth_service.terminate_user_sessions(user_id)
        
        # Log password reset event
        if actor:
            await audit_service.log_user_management(
                action="password_reset",
                actor_id=actor.id,
                target_user_id=user_id,
                target_username=user.username,
                details={"force_change": force_change},
            )
    
    async def change_own_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change user's own password (self-service).
        
        Args:
            user_id: ID of user changing password
            current_password: Current password for verification
            new_password: New password
            
        Raises:
            ValueError: If validation fails or current password is incorrect
        """
        # Get user
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify current password
        if not auth_service.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Validate new password strength
        is_valid, error_msg = auth_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Check password history
        if auth_service.check_password_history(new_password, user.password_history):
            raise ValueError(
                f"Password was used recently. Please choose a different password."
            )
        
        # Hash new password
        new_hash = auth_service.hash_password(new_password)
        
        # Update password history
        new_history = auth_service.update_password_history(new_hash, user.password_history)
        
        # Update password in database
        query = """
            UPDATE users
            SET password_hash = ?,
                password_history = ?,
                must_change_password = false,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(
            query,
            [new_hash, new_history, str(user_id)],
        )
        
        # Log password change event
        await auth_service.log_auth_event(
            event_type="password_changed",
            user_id=user_id,
            username=user.username,
            details=json.dumps({"self_service": True}),
        )
    
    async def search_users(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[UserPublic], int]:
        """
        Search and filter users.
        
        Args:
            query: Search query for username or full name
            role: Filter by role
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of users, total count)
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append("(username LIKE ? OR full_name LIKE ?)")
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern])
        
        if role:
            where_clauses.append("role = ?")
            params.append(role)
        
        if is_active is not None:
            where_clauses.append("is_active = ?")
            params.append(is_active)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        db = get_db()
        with db.get_read_connection() as conn:
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM users WHERE {where_sql}",
                params,
            ).fetchone()
            total_count = count_result[0]
            
            # Get users
            result = conn.execute(
                f"""
                SELECT id, username, full_name, role, is_active,
                       must_change_password, created_at, updated_at
                FROM users
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        
        users = [
            UserPublic(
                id=row[0],
                username=row[1],
                full_name=row[2],
                role=row[3],
                is_active=row[4],
                must_change_password=row[5],
                created_at=row[6],
                updated_at=row[7],
            )
            for row in result
        ]
        
        return users, total_count
    
    async def _username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.
        
        Args:
            username: Username to check
            
        Returns:
            True if username exists, False otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM users WHERE username = ?",
                [username],
            ).fetchone()
            return result[0] > 0


# Global user service instance
user_service = UserService()
