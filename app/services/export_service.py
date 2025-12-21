"""Export service for generating CSV reports."""

import csv
from io import StringIO
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.database.connection import get_db


class ExportService:
    """Service for exporting data to CSV format."""
    
    async def export_packages_csv(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        recipient_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
    ) -> str:
        """
        Generate CSV export of packages with filters.
        
        Args:
            query: Search query for tracking_no or recipient name
            status: Filter by package status
            department: Filter by recipient department
            date_from: Filter packages created from this date
            date_to: Filter packages created until this date
            recipient_id: Filter by specific recipient
            created_by: Filter by operator who created the package
            
        Returns:
            CSV string with package data
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append(
                "(p.tracking_no LIKE ? OR r.name LIKE ?)"
            )
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern])
        
        if status:
            where_clauses.append("p.status = ?")
            params.append(status)
        
        if department:
            where_clauses.append("r.department = ?")
            params.append(department)
        
        if date_from:
            where_clauses.append("p.created_at >= ?")
            params.append(date_from)
        
        if date_to:
            where_clauses.append("p.created_at <= ?")
            params.append(date_to)
        
        if recipient_id:
            where_clauses.append("p.recipient_id = ?")
            params.append(str(recipient_id))
        
        if created_by:
            where_clauses.append("p.created_by = ?")
            params.append(str(created_by))
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Query packages
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                f"""
                SELECT 
                    p.tracking_no,
                    p.carrier,
                    r.name as recipient_name,
                    r.email as recipient_email,
                    r.department as recipient_department,
                    p.status,
                    p.notes,
                    u.full_name as created_by_name,
                    p.created_at,
                    p.updated_at
                FROM packages p
                JOIN recipients r ON p.recipient_id = r.id
                JOIN users u ON p.created_by = u.id
                WHERE {where_sql}
                ORDER BY p.created_at DESC
                """,
                params,
            ).fetchall()
        
        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Tracking Number",
            "Carrier",
            "Recipient Name",
            "Recipient Email",
            "Department",
            "Status",
            "Notes",
            "Created By",
            "Created At",
            "Updated At",
        ])
        
        # Write data rows
        for row in result:
            writer.writerow([
                row[0],  # tracking_no
                row[1],  # carrier
                row[2],  # recipient_name
                row[3],  # recipient_email
                row[4] or "",  # recipient_department
                row[5],  # status
                row[6] or "",  # notes
                row[7],  # created_by_name
                row[8],  # created_at
                row[9],  # updated_at
            ])
        
        return output.getvalue()


# Global export service instance
export_service = ExportService()

