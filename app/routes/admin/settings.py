"""Admin settings and audit log routes."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from app.decorators import get_current_user, require_role
from app.middleware.csrf import validate_csrf_token
from app.routes.auth import get_client_ip
from app.templates import templates


router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
@require_role("super_admin")
async def show_settings(request: Request):
    """Display system settings page."""
    from app.services.system_settings_service import system_settings_service
    from app.services.carrier_service import carrier_service

    user = get_current_user(request)
    qr_base_url = await system_settings_service.get_qr_base_url()
    carriers = await carrier_service.get_all_carriers()

    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": user,
            "qr_base_url": qr_base_url or "",
            "carriers": carriers,
        },
    )


@router.post("/settings/qr-base-url")
@require_role("super_admin")
async def update_qr_base_url(
    request: Request,
    qr_base_url: str = Form(...),
    csrf_token: str = Form(...),
):
    """Update QR code base URL."""
    from app.services.system_settings_service import system_settings_service

    user = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        client_ip = get_client_ip(request)
        await system_settings_service.set_qr_base_url(
            qr_base_url,
            actor_id=user.id,
            actor_username=user.username,
            ip_address=client_ip,
        )

        from app.services.carrier_service import carrier_service
        carriers = await carrier_service.get_all_carriers()

        return templates.TemplateResponse(
            "admin/settings.html",
            {
                "request": request,
                "user": user,
                "qr_base_url": qr_base_url,
                "carriers": carriers,
                "success": "QR code base URL updated successfully",
            },
        )
    except ValueError as e:
        from app.services.carrier_service import carrier_service
        carriers = await carrier_service.get_all_carriers()

        return templates.TemplateResponse(
            "admin/settings.html",
            {
                "request": request,
                "user": user,
                "qr_base_url": qr_base_url,
                "carriers": carriers,
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/audit-logs", response_class=HTMLResponse)
@require_role("super_admin")
async def view_audit_logs(
    request: Request,
    user_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """View audit logs with filtering and pagination."""
    from app.services.audit_service import audit_service

    user = get_current_user(request)

    start_date_dt = None
    end_date_dt = None

    if start_date:
        try:
            start_date_dt = datetime.fromisoformat(start_date)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_dt = datetime.fromisoformat(end_date)
        except ValueError:
            pass

    user_uuid = None
    if user_id:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            pass

    events, total_count = await audit_service.get_auth_events(
        user_id=user_uuid,
        event_type=event_type,
        username=username,
        start_date=start_date_dt,
        end_date=end_date_dt,
        limit=limit,
        offset=offset,
    )

    event_types = [
        "login",
        "login_failed",
        "logout",
        "password_changed",
        "password_reset",
        "user_management",
        "recipient_import",
    ]

    context = {
        "request": request,
        "user": user,
        "events": events,
        "event_types": event_types,
        "filters": {
            "user_id": user_id,
            "event_type": event_type,
            "username": username,
            "start_date": start_date,
            "end_date": end_date,
        },
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "current_page": (offset // limit) + 1,
            "total_pages": (total_count + limit - 1) // limit,
        },
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("admin/audit_logs_table_partial.html", context)

    return templates.TemplateResponse("admin/audit_logs.html", context)
