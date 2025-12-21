"""Dashboard service for summary statistics and reporting."""

from datetime import datetime, date
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.database.connection import get_db


class DashboardStats(BaseModel):
    """Dashboard summary statistics."""
    
    packages_today: int
    packages_awaiting_pickup: int
    packages_delivered_today: int
    total_packages: int


class RecipientStats(BaseModel):
    """Recipient statistics for top recipients."""
    
    recipient_id: str
    recipient_name: str
    department: Optional[str]
    package_count: int


class StatusDistribution(BaseModel):
    """Package count by status."""
    
    status: str
    count: int


class DashboardService:
    """Service for dashboard statistics and reporting."""
    
    async def get_summary_stats(self) -> DashboardStats:
        """
        Get summary statistics for dashboard (< 200ms response time).
        
        Returns:
            DashboardStats with key metrics
        """
        db = get_db()
        with db.get_read_connection() as conn:
            # Get packages registered today
            packages_today = conn.execute(
                """
                SELECT COUNT(*)
                FROM packages
                WHERE DATE(created_at) = CURRENT_DATE
                """
            ).fetchone()[0]
            
            # Get packages awaiting pickup
            packages_awaiting_pickup = conn.execute(
                """
                SELECT COUNT(*)
                FROM packages
                WHERE status = 'awaiting_pickup'
                """
            ).fetchone()[0]
            
            # Get packages delivered today
            packages_delivered_today = conn.execute(
                """
                SELECT COUNT(*)
                FROM packages
                WHERE status = 'delivered'
                AND DATE(updated_at) = CURRENT_DATE
                """
            ).fetchone()[0]
            
            # Get total packages
            total_packages = conn.execute(
                """
                SELECT COUNT(*)
                FROM packages
                """
            ).fetchone()[0]
        
        return DashboardStats(
            packages_today=packages_today,
            packages_awaiting_pickup=packages_awaiting_pickup,
            packages_delivered_today=packages_delivered_today,
            total_packages=total_packages,
        )
    
    async def get_top_recipients(
        self,
        limit: int = 5,
        period: str = "month"
    ) -> List[RecipientStats]:
        """
        Get top recipients by package count for current period.
        
        Args:
            limit: Maximum number of recipients to return (default 5)
            period: Time period - 'month', 'week', or 'all' (default 'month')
            
        Returns:
            List of RecipientStats ordered by package count descending
        """
        # Build date filter based on period
        date_filter = ""
        if period == "month":
            date_filter = "AND DATE_TRUNC('month', p.created_at) = DATE_TRUNC('month', CURRENT_DATE)"
        elif period == "week":
            date_filter = "AND DATE_TRUNC('week', p.created_at) = DATE_TRUNC('week', CURRENT_DATE)"
        # 'all' has no date filter
        
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                f"""
                SELECT r.id, r.name, r.department, COUNT(p.id) as package_count
                FROM recipients r
                JOIN packages p ON p.recipient_id = r.id
                WHERE 1=1 {date_filter}
                GROUP BY r.id, r.name, r.department
                ORDER BY package_count DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        
        return [
            RecipientStats(
                recipient_id=str(row[0]),
                recipient_name=row[1],
                department=row[2],
                package_count=row[3],
            )
            for row in result
        ]
    
    async def get_status_distribution(self) -> List[StatusDistribution]:
        """
        Get package count by status.
        
        Returns:
            List of StatusDistribution with counts for each status
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM packages
                GROUP BY status
                ORDER BY count DESC
                """
            ).fetchall()
        
        return [
            StatusDistribution(
                status=row[0],
                count=row[1],
            )
            for row in result
        ]
    
    async def get_department_list(self) -> List[str]:
        """
        Get list of unique departments from recipients.
        
        Returns:
            List of department names
        """
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT DISTINCT department
                FROM recipients
                WHERE department IS NOT NULL
                ORDER BY department
                """
            ).fetchall()
        
        return [row[0] for row in result]


# Global dashboard service instance
dashboard_service = DashboardService()

