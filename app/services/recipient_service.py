"""Recipient management service for CRUD operations."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from app.models import (
    Recipient,
    RecipientCreate,
    RecipientUpdate,
    RecipientPublic,
    RecipientSearchResult,
    User,
)
from app.database.connection import get_db
from app.database.write_queue import get_write_queue
from app.utils.validation import is_valid_email


class RecipientService:
    """Service for recipient management operations."""
    
    async def create_recipient(
        self,
        recipient_data: RecipientCreate,
    ) -> Recipient:
        """
        Create a new recipient.
        
        Args:
            recipient_data: Recipient creation data
            
        Returns:
            Created recipient object
            
        Raises:
            ValueError: If employee_id already exists or validation fails
        """
        # Check if employee_id already exists
        if await self._employee_id_exists(recipient_data.employee_id):
            raise ValueError(f"Employee ID '{recipient_data.employee_id}' already exists")
        
        # Check if email already exists
        if await self._email_exists(recipient_data.email):
            raise ValueError(f"Email '{recipient_data.email}' already exists")
        
        # Validate email format (pydantic EmailStr already validates, but double-check)
        if not is_valid_email(recipient_data.email):
            raise ValueError(f"Invalid email format: {recipient_data.email}")
        
        # Validate department is provided and not empty
        if not recipient_data.department or not recipient_data.department.strip():
            raise ValueError("Department is required and cannot be empty")
        department_value = recipient_data.department.strip()
        
        # Insert recipient into database (explicitly setting all columns to avoid missing defaults)
        query = """
            INSERT INTO recipients (
                id,
                employee_id,
                name,
                email,
                department,
                phone,
                location,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, employee_id, name, email, department, phone, location,
                      is_active, created_at, updated_at
        """
        timestamp = datetime.utcnow()
        recipient_id = uuid4()
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [
                str(recipient_id),
                recipient_data.employee_id,
                recipient_data.name,
                recipient_data.email,
                department_value,
                recipient_data.phone,
                recipient_data.location,
                timestamp,
                timestamp,
            ],
            return_result=True,
        )
        
        row = result[0]
        recipient = Recipient(
            id=row[0],
            employee_id=row[1],
            name=row[2],
            email=row[3],
            department=row[4],
            phone=row[5],
            location=row[6],
            is_active=row[7],
            created_at=row[8],
            updated_at=row[9],
        )
        
        return recipient
    
    async def get_recipient_by_id(self, recipient_id: UUID) -> Optional[Recipient]:
        """
        Get a recipient by ID.
        
        Args:
            recipient_id: Recipient ID to retrieve
            
        Returns:
            Recipient object if found, None otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, employee_id, name, email, department, phone, location,
                       is_active, created_at, updated_at
                FROM recipients
                WHERE id = ?
                """,
                [str(recipient_id)],
            ).fetchone()
            
            if not result:
                return None
            
            return Recipient(
                id=result[0],
                employee_id=result[1],
                name=result[2],
                email=result[3],
                department=result[4],
                phone=result[5],
                location=result[6],
                is_active=result[7],
                created_at=result[8],
                updated_at=result[9],
            )
    
    async def get_recipient_by_employee_id(self, employee_id: str) -> Optional[Recipient]:
        """
        Get a recipient by employee ID.
        
        Args:
            employee_id: Employee ID to retrieve
            
        Returns:
            Recipient object if found, None otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, employee_id, name, email, department, phone, location,
                       is_active, created_at, updated_at
                FROM recipients
                WHERE employee_id = ?
                """,
                [employee_id],
            ).fetchone()
            
            if not result:
                return None
            
            return Recipient(
                id=result[0],
                employee_id=result[1],
                name=result[2],
                email=result[3],
                department=result[4],
                phone=result[5],
                location=result[6],
                is_active=result[7],
                created_at=result[8],
                updated_at=result[9],
            )
    
    async def update_recipient(
        self,
        recipient_id: UUID,
        recipient_data: RecipientUpdate,
    ) -> Recipient:
        """
        Update recipient information.
        
        Args:
            recipient_id: ID of recipient to update
            recipient_data: Updated recipient data
            
        Returns:
            Updated recipient object
            
        Raises:
            ValueError: If recipient not found or validation fails
        """
        recipient = await self.get_recipient_by_id(recipient_id)
        if not recipient:
            raise ValueError("Recipient not found")
        
        replacement_name = recipient.name
        replacement_email = recipient.email
        replacement_department = recipient.department
        replacement_phone = recipient.phone
        replacement_location = recipient.location
        
        if recipient_data.name is not None:
            replacement_name = recipient_data.name
        
        if recipient_data.email is not None:
            if not is_valid_email(recipient_data.email):
                raise ValueError(f"Invalid email format: {recipient_data.email}")
            # Check if email already exists (excluding current recipient)
            if await self._email_exists(recipient_data.email, exclude_id=recipient_id):
                raise ValueError(f"Email '{recipient_data.email}' already exists")
            replacement_email = recipient_data.email
        
        if recipient_data.department is not None:
            department_value = recipient_data.department.strip()
            if not department_value:
                raise ValueError("Department is required and cannot be empty")
            replacement_department = department_value
        
        if recipient_data.phone is not None:
            replacement_phone = recipient_data.phone
        
        if recipient_data.location is not None:
            replacement_location = recipient_data.location
        
        if (
            replacement_name == recipient.name
            and replacement_email == recipient.email
            and replacement_department == recipient.department
            and replacement_phone == recipient.phone
            and replacement_location == recipient.location
        ):
            return recipient  # No changes

        replacement_updated_at = datetime.utcnow()

        # Avoid DuckDB UPDATE on recipients entirely. Use row replacement with
        # separate fresh write connections for delete and insert. Also close the
        # thread-local read connection first so the replacement does not reuse a
        # stale read transaction state while re-inserting the same primary key.
        db = get_db()
        db.close()

        with db.get_write_connection() as conn:
            conn.execute(
                "DELETE FROM recipients WHERE id = ?",
                [str(recipient_id)],
            )

        with db.get_write_connection() as conn:
            conn.execute(
                """
                INSERT INTO recipients (
                    id,
                    employee_id,
                    name,
                    email,
                    department,
                    phone,
                    location,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(recipient.id),
                    recipient.employee_id,
                    replacement_name,
                    replacement_email,
                    replacement_department,
                    replacement_phone,
                    replacement_location,
                    recipient.is_active,
                    recipient.created_at,
                    replacement_updated_at,
                ],
            )
            result = conn.execute(
                """
                SELECT id, employee_id, name, email, department, phone, location,
                       is_active, created_at, updated_at
                FROM recipients
                WHERE id = ?
                """,
                [str(recipient_id)],
            ).fetchone()

        if not result:
            raise ValueError("Recipient not found after update")
        
        row = result
        updated_recipient = Recipient(
            id=row[0],
            employee_id=row[1],
            name=row[2],
            email=row[3],
            department=row[4],
            phone=row[5],
            location=row[6],
            is_active=row[7],
            created_at=row[8],
            updated_at=row[9],
        )
        
        return updated_recipient
    
    async def deactivate_recipient(
        self,
        recipient_id: UUID,
    ) -> None:
        """
        Deactivate a recipient (soft delete).
        
        Args:
            recipient_id: ID of recipient to deactivate
            
        Raises:
            ValueError: If recipient not found
        """
        # Get recipient to verify it exists
        recipient = await self.get_recipient_by_id(recipient_id)
        if not recipient:
            raise ValueError("Recipient not found")
        
        # Deactivate recipient
        query = """
            UPDATE recipients
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        write_queue = await get_write_queue()
        await write_queue.execute(query, [str(recipient_id)])
    
    async def search_recipients(
        self,
        query: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10,
    ) -> List[RecipientSearchResult]:
        """
        Search recipients for autocomplete (< 200ms response time).
        
        Args:
            query: Search query for name, email, or employee_id
            active_only: Only return active recipients
            limit: Maximum number of results
            
        Returns:
            List of recipient search results
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append(
                "(name LIKE ? OR email LIKE ? OR employee_id LIKE ?)"
            )
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if active_only:
            where_clauses.append("is_active = true")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get recipients
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                f"""
                SELECT id, employee_id, name, email, department
                FROM recipients
                WHERE {where_sql}
                ORDER BY name ASC
                LIMIT ?
                """,
                params + [limit],
            ).fetchall()
        
        recipients = [
            RecipientSearchResult(
                id=row[0],
                employee_id=row[1],
                name=row[2],
                email=row[3],
                department=row[4],
            )
            for row in result
        ]
        
        return recipients
    
    async def list_recipients(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[List[RecipientPublic], int]:
        """
        List and filter recipients with pagination.
        
        Args:
            query: Search query for name, email, or employee_id
            department: Filter by department
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of recipients, total count)
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append(
                "(name LIKE ? OR email LIKE ? OR employee_id LIKE ?)"
            )
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if department:
            where_clauses.append("department LIKE ?")
            params.append(f"%{department}%")
        
        if is_active is not None:
            where_clauses.append("is_active = ?")
            params.append(is_active)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        db = get_db()
        with db.get_read_connection() as conn:
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM recipients WHERE {where_sql}",
                params,
            ).fetchone()
            total_count = count_result[0] if count_result else 0
            
            # Get recipients
            result = conn.execute(
                f"""
                SELECT id, employee_id, name, email, department, phone, location,
                       is_active, created_at, updated_at
                FROM recipients
                WHERE {where_sql}
                ORDER BY name ASC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        
        recipients = [
            RecipientPublic(
                id=row[0],
                employee_id=row[1],
                name=row[2],
                email=row[3],
                department=row[4],
                phone=row[5],
                location=row[6],
                is_active=row[7],
                created_at=row[8],
                updated_at=row[9],
            )
            for row in result
        ]
        
        return recipients, total_count
    
    async def _employee_id_exists(self, employee_id: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if an employee_id already exists.
        
        Args:
            employee_id: Employee ID to check
            exclude_id: Optional recipient ID to exclude from check (for updates)
            
        Returns:
            True if employee_id exists, False otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            if exclude_id:
                result = conn.execute(
                    "SELECT COUNT(*) FROM recipients WHERE employee_id = ? AND id != ?",
                    [employee_id, str(exclude_id)],
                ).fetchone()
            else:
                result = conn.execute(
                    "SELECT COUNT(*) FROM recipients WHERE employee_id = ?",
                    [employee_id],
                ).fetchone()
            return (result[0] if result else 0) > 0
    
    async def _email_exists(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if an email already exists.
        
        Args:
            email: Email to check
            exclude_id: Optional recipient ID to exclude from check (for updates)
            
        Returns:
            True if email exists, False otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            if exclude_id:
                result = conn.execute(
                    "SELECT COUNT(*) FROM recipients WHERE email = ? AND id != ?",
                    [email, str(exclude_id)],
                ).fetchone()
            else:
                result = conn.execute(
                    "SELECT COUNT(*) FROM recipients WHERE email = ?",
                    [email],
                ).fetchone()
            return (result[0] if result else 0) > 0


# Global recipient service instance
recipient_service = RecipientService()
