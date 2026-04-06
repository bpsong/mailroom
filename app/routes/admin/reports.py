"""Admin reporting routes."""
from datetime import datetime
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse

from app.decorators import get_current_user, require_role
from app.models import PackageFilters, Pagination
from app.services.package_service import package_service
from app.templates import templates


router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
@require_role("admin")
async def reports_page(request: Request):
    """Render reports page with filters and export functionality."""
    from app.services.dashboard_service import dashboard_service
    from app.services.user_service import user_service

    user = get_current_user(request)
    departments = await dashboard_service.get_department_list()
    operators, _ = await user_service.search_users(
        role="operator",
        is_active=True,
        limit=100,
        offset=0,
    )

    return templates.TemplateResponse(
        "admin/reports.html",
        {
            "request": request,
            "user": user,
            "departments": departments,
            "operators": operators,
        },
    )


@router.get("/reports/preview", response_class=HTMLResponse)
@require_role("admin")
async def preview_packages_report(
    request: Request,
    query: Optional[str] = Query(None),
    package_status: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recipient_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
):
    """Preview packages that match the report filters."""
    user = get_current_user(request)

    date_from_dt = None
    date_to_dt = None

    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    recipient_uuid = None
    created_by_uuid = None

    if recipient_id:
        try:
            recipient_uuid = UUID(recipient_id)
        except ValueError:
            pass

    if created_by:
        try:
            created_by_uuid = UUID(created_by)
        except ValueError:
            pass

    filters = PackageFilters(
        query=query,
        status=package_status,
        department=department,
        date_from=date_from_dt,
        date_to=date_to_dt,
        recipient_id=recipient_uuid,
        created_by=created_by_uuid,
    )

    packages, total_count = await package_service.search_packages(
        filters=filters,
        pagination=Pagination(limit=10, offset=0),
    )

    return templates.TemplateResponse(
        "admin/reports_preview.html",
        {
            "request": request,
            "user": user,
            "packages": packages,
            "total_count": total_count,
        },
    )


@router.get("/reports/export")
@require_role("admin")
async def export_packages_report(
    request: Request,
    query: Optional[str] = Query(None),
    package_status: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recipient_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
):
    """Export packages report as CSV with filters."""
    from app.services.export_service import export_service

    user = get_current_user(request)
    date_from_dt = None
    date_to_dt = None

    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use ISO format (YYYY-MM-DD)",
            )

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use ISO format (YYYY-MM-DD)",
            )

    recipient_uuid = None
    created_by_uuid = None

    if recipient_id:
        try:
            recipient_uuid = UUID(recipient_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid recipient_id format",
            )

    if created_by:
        try:
            created_by_uuid = UUID(created_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid created_by format",
            )

    try:
        csv_content = await export_service.export_packages_csv(
            query=query,
            status=package_status,
            department=department,
            date_from=date_from_dt,
            date_to=date_to_dt,
            recipient_id=recipient_uuid,
            created_by=created_by_uuid,
        )

        output = BytesIO(csv_content.encode("utf-8"))
        filename = f"packages_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export packages: {str(e)}",
        )
