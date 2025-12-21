"""Dashboard routes for all users."""

from datetime import date
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templates import templates
from app.decorators import require_auth, get_current_user
from app.services.dashboard_service import dashboard_service


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_class=HTMLResponse)
@require_auth
async def get_dashboard(request: Request):
    """
    Get dashboard with summary statistics.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dashboard HTML page with statistics
    """
    user = get_current_user(request)
    
    # Get dashboard statistics
    stats = await dashboard_service.get_summary_stats()
    top_recipients = await dashboard_service.get_top_recipients(limit=5, period="month")
    status_distribution = await dashboard_service.get_status_distribution()
    
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "top_recipients": top_recipients,
            "status_distribution": status_distribution,
            "today": date.today().isoformat(),
        },
    )
