"""Recipient routes for searching and autocomplete."""

from typing import List
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

from app.templates import templates
from app.decorators import require_auth, get_current_user
from app.services.recipient_service import recipient_service
from app.models import RecipientSearchResult


router = APIRouter(prefix="/recipients", tags=["recipients"])


@router.get("", response_class=HTMLResponse)
@require_auth
async def list_recipients_page(
    request: Request,
    query: str = Query("", alias="q"),
    department: str = Query("", alias="dept"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=10, le=100),
):
    """
    Display recipient list page (read-only for operators).
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        query: Search query for name, email, or employee_id
        department: Filter by department
        page: Page number for pagination
        limit: Results per page
        
    Returns:
        Recipient list HTML page
    """
    user = get_current_user(request)
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Search recipients (active only for operators)
    recipients, total_count = await recipient_service.list_recipients(
        query=query if query else None,
        department=department if department else None,
        is_active=True,
        offset=offset,
        limit=limit,
    )
    
    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit
    
    return templates.TemplateResponse(
        "recipients/list.html",
        {
            "request": request,
            "user": user,
            "recipients": recipients,
            "query": query,
            "department": department,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
    )


@router.get("/search")
@require_auth
async def search_recipients(
    request: Request,
    q: str = Query("", min_length=0, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Search recipients for autocomplete (< 200ms response time).
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        q: Search query string
        limit: Maximum number of results
        
    Returns:
        HTML with matching recipients or JSON based on Accept header
    """
    user = get_current_user(request)
    
    # Search recipients (active only for autocomplete)
    recipients = await recipient_service.search_recipients(
        query=q if q else None,
        active_only=True,
        limit=limit,
    )
    
    # Check if request wants HTML (from HTMX) or JSON
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header or "hx-request" in request.headers:
        # Return HTML for HTMX
        return templates.TemplateResponse(
            "components/recipient_search_results.html",
            {
                "request": request,
                "recipients": recipients,
            },
        )
    else:
        # Return JSON for API calls
        return recipients
