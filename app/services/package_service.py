"""Package management service for CRUD operations."""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.models import (
    Package,
    PackageCreate,
    PackageUpdate,
    PackageStatusUpdate,
    PackageEvent,
    PackageEventCreate,
    PackagePublic,
    PackageDetail,
    PackageFilters,
    Pagination,
    Attachment,
    AttachmentCreate,
    User,
)
from app.database.connection import get_db
from app.database.write_queue import get_write_queue
from app.services.recipient_service import recipient_service
from app.services.file_service import file_service
from app.services.audit_service import audit_service


class PackageService:
    """Service for package management operations."""
    
    VALID_STATUSES = {
        "registered",
        "awaiting_pickup",
        "out_for_delivery",
        "delivered",
        "returned"
    }
    
    async def create_package(
        self,
        package_data: PackageCreate,
        actor: User,
    ) -> Package:
        """
        Create a new package with initial status 'registered'.
        
        Args:
            package_data: Package creation data
            actor: User creating the package
            
        Returns:
            Created package object
            
        Raises:
            ValueError: If recipient is not found or not active
        """
        # Validate recipient exists and is active
        recipient = await recipient_service.get_recipient_by_id(package_data.recipient_id)
        if not recipient:
            raise ValueError(f"Recipient with ID '{package_data.recipient_id}' not found")
        
        if not recipient.is_active:
            raise ValueError(f"Recipient '{recipient.name}' is not active")
        
        # Insert package into database with initial status 'registered'
        query = """
            INSERT INTO packages (
                id,
                tracking_no,
                carrier,
                recipient_id,
                status,
                notes,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 'registered', ?, ?, ?, ?)
            RETURNING id, tracking_no, carrier, recipient_id, status, notes,
                      created_by, created_at, updated_at
        """
        package_id = uuid4()
        timestamp = datetime.utcnow()
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [
                str(package_id),
                package_data.tracking_no,
                package_data.carrier,
                str(package_data.recipient_id),
                package_data.notes,
                str(actor.id),
                timestamp,
                timestamp,
            ],
            return_result=True,
        )
        
        row = result[0]
        package = Package(
            id=row[0],
            tracking_no=row[1],
            carrier=row[2],
            recipient_id=row[3],
            status=row[4],
            notes=row[5],
            created_by=row[6],
            created_at=row[7],
            updated_at=row[8],
        )
        
        # Create initial package event
        await self._create_package_event(
            package_id=package.id,
            old_status=None,
            new_status="registered",
            notes=f"Package registered by {actor.full_name}",
            actor_id=actor.id,
        )
        
        # Log to audit service
        await audit_service.log_package_event(
            package_id=package.id,
            old_status=None,
            new_status="registered",
            actor_id=actor.id,
            notes=f"Package registered by {actor.full_name}",
        )
        
        return package
    
    async def get_package_by_id(self, package_id: UUID) -> Optional[Package]:
        """
        Get a package by ID.
        
        Args:
            package_id: Package ID to retrieve
            
        Returns:
            Package object if found, None otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, tracking_no, carrier, recipient_id, status, notes,
                       created_by, created_at, updated_at
                FROM packages
                WHERE id = ?
                """,
                [str(package_id)],
            ).fetchone()
            
            if not result:
                return None
            
            return Package(
                id=result[0],
                tracking_no=result[1],
                carrier=result[2],
                recipient_id=result[3],
                status=result[4],
                notes=result[5],
                created_by=result[6],
                created_at=result[7],
                updated_at=result[8],
            )
    
    async def update_status(
        self,
        package_id: UUID,
        status_update: PackageStatusUpdate,
        actor: User,
    ) -> Package:
        """
        Update package status and create event record.
        
        Args:
            package_id: ID of package to update
            status_update: New status and optional notes
            actor: User performing the update
            
        Returns:
            Updated package object
            
        Raises:
            ValueError: If package not found or invalid status
        """
        # Validate status
        if status_update.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status_update.status}'. "
                f"Must be one of: {', '.join(self.VALID_STATUSES)}"
            )
        
        # Get current package
        package = await self.get_package_by_id(package_id)
        if not package:
            raise ValueError("Package not found")
        
        old_status = package.status
        
        # Update package status
        query = """
            UPDATE packages
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, tracking_no, carrier, recipient_id, status, notes,
                      created_by, created_at, updated_at
        """
        
        write_queue = await get_write_queue()
        try:
            result = await write_queue.execute(
                query,
                [status_update.status, status_update.notes, str(package_id)],
                return_result=True,
            )
        except Exception as e:
            raise ValueError(f"Failed to update package status: {str(e)}")
        
        row = result[0]
        updated_package = Package(
            id=row[0],
            tracking_no=row[1],
            carrier=row[2],
            recipient_id=row[3],
            status=row[4],
            notes=row[5],
            created_by=row[6],
            created_at=row[7],
            updated_at=row[8],
        )
        
        # Create package event
        await self._create_package_event(
            package_id=package_id,
            old_status=old_status,
            new_status=status_update.status,
            notes=status_update.notes,
            actor_id=actor.id,
        )
        
        # Log to audit service
        await audit_service.log_package_event(
            package_id=package_id,
            old_status=old_status,
            new_status=status_update.status,
            actor_id=actor.id,
            notes=status_update.notes,
        )
        
        return updated_package
    
    async def search_packages(
        self,
        filters: PackageFilters,
        pagination: Pagination,
    ) -> Tuple[List[PackagePublic], int]:
        """
        Search packages with filters and pagination (< 200ms response time).
        
        Args:
            filters: Search and filter criteria
            pagination: Pagination parameters
            
        Returns:
            Tuple of (list of packages, total count)
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if filters.query:
            where_clauses.append(
                "(p.tracking_no LIKE ? OR r.name LIKE ?)"
            )
            search_pattern = f"%{filters.query}%"
            params.extend([search_pattern, search_pattern])
        
        if filters.status:
            where_clauses.append("p.status = ?")
            params.append(filters.status)
        
        if filters.department:
            where_clauses.append("r.department = ?")
            params.append(filters.department)
        
        if filters.date_from:
            where_clauses.append("p.created_at >= ?")
            params.append(filters.date_from)
        
        if filters.date_to:
            where_clauses.append("p.created_at <= ?")
            params.append(filters.date_to)
        
        if filters.recipient_id:
            where_clauses.append("p.recipient_id = ?")
            params.append(str(filters.recipient_id))
        
        if filters.created_by:
            where_clauses.append("p.created_by = ?")
            params.append(str(filters.created_by))
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        db = get_db()
        with db.get_read_connection() as conn:
            count_result = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM packages p
                JOIN recipients r ON p.recipient_id = r.id
                WHERE {where_sql}
                """,
                params,
            ).fetchone()
            total_count = count_result[0]
            
            # Get packages with recipient and creator info
            result = conn.execute(
                f"""
                SELECT p.id, p.tracking_no, p.carrier, p.recipient_id,
                       r.name as recipient_name, r.department as recipient_department,
                       p.status, p.notes, p.created_by,
                       u.full_name as created_by_name,
                       p.created_at, p.updated_at
                FROM packages p
                JOIN recipients r ON p.recipient_id = r.id
                JOIN users u ON p.created_by = u.id
                WHERE {where_sql}
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [pagination.limit, pagination.offset],
            ).fetchall()
        
        packages = [
            PackagePublic(
                id=row[0],
                tracking_no=row[1],
                carrier=row[2],
                recipient_id=row[3],
                recipient_name=row[4],
                recipient_department=row[5],
                status=row[6],
                notes=row[7],
                created_by=row[8],
                created_by_name=row[9],
                created_at=row[10],
                updated_at=row[11],
            )
            for row in result
        ]
        
        return packages, total_count
    
    async def get_package_detail(self, package_id: UUID) -> Optional[PackageDetail]:
        """
        Get detailed package information with timeline.
        
        Args:
            package_id: Package ID to retrieve
            
        Returns:
            PackageDetail object if found, None otherwise
        """
        db = get_db()
        with db.get_read_connection() as conn:
            # Get package with recipient and creator info
            result = conn.execute(
                """
                SELECT p.id, p.tracking_no, p.carrier, p.recipient_id,
                       r.name as recipient_name, r.email as recipient_email,
                       r.department as recipient_department,
                       p.status, p.notes, p.created_by,
                       u.full_name as created_by_name,
                       p.created_at, p.updated_at
                FROM packages p
                JOIN recipients r ON p.recipient_id = r.id
                JOIN users u ON p.created_by = u.id
                WHERE p.id = ?
                """,
                [str(package_id)],
            ).fetchone()
            
            if not result:
                return None
            
            # Get package timeline
            timeline = await self.get_package_timeline(package_id)
            
            return PackageDetail(
                id=result[0],
                tracking_no=result[1],
                carrier=result[2],
                recipient_id=result[3],
                recipient_name=result[4],
                recipient_email=result[5],
                recipient_department=result[6],
                status=result[7],
                notes=result[8],
                created_by=result[9],
                created_by_name=result[10],
                created_at=result[11],
                updated_at=result[12],
                timeline=timeline,
            )
    
    async def get_package_timeline(self, package_id: UUID) -> List[PackageEvent]:
        """
        Get status history timeline for a package.
        
        Args:
            package_id: Package ID
            
        Returns:
            List of package events ordered by creation time
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, package_id, old_status, new_status, notes,
                       actor_id, created_at
                FROM package_events
                WHERE package_id = ?
                ORDER BY created_at ASC
                """,
                [str(package_id)],
            ).fetchall()
        
        events = [
            PackageEvent(
                id=row[0],
                package_id=row[1],
                old_status=row[2],
                new_status=row[3],
                notes=row[4],
                actor_id=row[5],
                created_at=row[6],
            )
            for row in result
        ]
        
        return events
    
    async def attach_photo(
        self,
        package_id: UUID,
        file: UploadFile,
        actor: User,
    ) -> Attachment:
        """
        Attach a photo to a package.
        
        Args:
            package_id: Package ID
            file: Uploaded photo file
            actor: User uploading the photo
            
        Returns:
            Created attachment object
            
        Raises:
            ValueError: If package not found or file validation fails
        """
        # Verify package exists
        package = await self.get_package_by_id(package_id)
        if not package:
            raise ValueError("Package not found")
        
        # Save file
        file_path, mime_type, file_size = await file_service.save_upload(
            file,
            category="packages"
        )
        
        # Create attachment record
        query = """
            INSERT INTO attachments (
                id,
                package_id,
                filename,
                file_path,
                mime_type,
                file_size,
                uploaded_by,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, package_id, filename, file_path, mime_type, file_size,
                      uploaded_by, created_at
        """
        attachment_id = uuid4()
        timestamp = datetime.utcnow()
        
        write_queue = await get_write_queue()
        result = await write_queue.execute(
            query,
            [
                str(attachment_id),
                str(package_id),
                file.filename or "photo.jpg",
                file_path,
                mime_type,
                file_size,
                str(actor.id),
                timestamp,
            ],
            return_result=True,
        )
        
        row = result[0]
        attachment = Attachment(
            id=row[0],
            package_id=row[1],
            filename=row[2],
            file_path=row[3],
            mime_type=row[4],
            file_size=row[5],
            uploaded_by=row[6],
            created_at=row[7],
        )
        
        return attachment
    
    async def get_package_attachments(self, package_id: UUID) -> List[Attachment]:
        """
        Get all attachments for a package.
        
        Args:
            package_id: Package ID
            
        Returns:
            List of attachments
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, package_id, filename, file_path, mime_type, file_size,
                       uploaded_by, created_at
                FROM attachments
                WHERE package_id = ?
                ORDER BY created_at ASC
                """,
                [str(package_id)],
            ).fetchall()
        
        attachments = [
            Attachment(
                id=row[0],
                package_id=row[1],
                filename=row[2],
                file_path=row[3],
                mime_type=row[4],
                file_size=row[5],
                uploaded_by=row[6],
                created_at=row[7],
            )
            for row in result
        ]
        
        return attachments
    
    async def _create_package_event(
        self,
        package_id: UUID,
        old_status: Optional[str],
        new_status: str,
        notes: Optional[str],
        actor_id: UUID,
    ) -> None:
        """
        Create a package event record.
        
        Args:
            package_id: Package ID
            old_status: Previous status (None for initial registration)
            new_status: New status
            notes: Optional notes
            actor_id: User who performed the action
        """
        query = """
            INSERT INTO package_events (
                id,
                package_id,
                old_status,
                new_status,
                notes,
                actor_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        event_id = uuid4()
        timestamp = datetime.utcnow()
        
        write_queue = await get_write_queue()
        await write_queue.execute(
            query,
            [
                str(event_id),
                str(package_id),
                old_status,
                new_status,
                notes,
                str(actor_id),
                timestamp,
            ],
        )


# Global package service instance
package_service = PackageService()
