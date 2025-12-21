"""Package management routes for all users."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from app.templates import templates
from app.decorators import require_auth, get_current_user
from app.middleware.csrf import validate_csrf_token
from app.models import (
    PackageCreate,
    PackageStatusUpdate,
    PackageFilters,
    Pagination,
)
from app.services.package_service import package_service
from app.services.qrcode_service import qrcode_service


router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_class=HTMLResponse)
@require_auth
async def list_packages(
    request: Request,
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    """
    List and search packages with filters.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        query: Search query for tracking_no or recipient name
        status: Filter by status
        department: Filter by recipient department
        date_from: Filter by created date from
        date_to: Filter by created date to
        page: Page number (1-indexed)
        limit: Items per page
        
    Returns:
        HTML page with package list
    """
    user = get_current_user(request)
    
    # Parse date filters
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
    
    # Build filters
    filters = PackageFilters(
        query=query,
        status=status,
        department=department,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )
    
    # Calculate pagination
    offset = (page - 1) * limit
    pagination = Pagination(limit=limit, offset=offset)
    
    # Search packages
    packages, total_count = await package_service.search_packages(filters, pagination)
    
    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit
    
    return templates.TemplateResponse(
        "packages/list.html",
        {
            "request": request,
            "user": user,
            "packages": packages,
            "filters": {
                "query": query,
                "status": status,
                "department": department,
                "date_from": date_from,
                "date_to": date_to,
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        },
    )


@router.get("/new", response_class=HTMLResponse)
@require_auth
async def show_register_form(request: Request):
    """
    Show package registration form.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML page with registration form
    """
    user = get_current_user(request)
    
    return templates.TemplateResponse(
        "packages/register.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/new")
@require_auth
async def register_package(
    request: Request,
    tracking_no: str = Form(...),
    carrier: str = Form(...),
    recipient_id: str = Form(...),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    csrf_token: str = Form(...),
):
    """
    Register a new package with optional photo.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        tracking_no: Package tracking number
        carrier: Carrier name
        recipient_id: Recipient UUID
        notes: Optional notes
        photo: Optional photo file
        
    Returns:
        Redirect to package detail page or error
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        # Create package
        package_data = PackageCreate(
            tracking_no=tracking_no,
            carrier=carrier,
            recipient_id=UUID(recipient_id),
            notes=notes,
        )
        
        package = await package_service.create_package(package_data, user)
        
        # Attach photo if provided
        if photo and photo.filename:
            await package_service.attach_photo(package.id, photo, user)
        
        # Return success response (HTMX will handle redirect)
        return templates.TemplateResponse(
            "packages/register_success.html",
            {
                "request": request,
                "user": user,
                "package": package,
            },
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering package: {str(e)}")


@router.get("/{package_id}", response_class=HTMLResponse)
@require_auth
async def get_package_details(request: Request, package_id: str):
    """
    Get package details with timeline.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        package_id: ID of package to view
        
    Returns:
        HTML page with package details and timeline
    """
    user = get_current_user(request)
    
    try:
        package_uuid = UUID(package_id)
        package_detail = await package_service.get_package_detail(package_uuid)
        
        if not package_detail:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Get attachments
        attachments = await package_service.get_package_attachments(package_uuid)
        
        # Generate QR code base64 using configured base URL
        fallback_url = str(request.base_url).rstrip('/')
        qr_code_base64 = await qrcode_service.get_qr_code_base64(package_uuid, fallback_url)
        
        return templates.TemplateResponse(
            "packages/detail.html",
            {
                "request": request,
                "user": user,
                "package": package_detail,
                "attachments": attachments,
                "qr_code_data": qr_code_base64,
            },
        )
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package ID")


@router.post("/{package_id}/status")
@require_auth
async def update_package_status(
    request: Request,
    package_id: str,
    status: str = Form(...),
    notes: Optional[str] = Form(None),
    csrf_token: str = Form(...),
):
    """
    Update package status.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        package_id: ID of package to update
        status: New status
        notes: Optional notes
        
    Returns:
        Updated package information (HTMX partial)
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        package_uuid = UUID(package_id)
        
        status_update = PackageStatusUpdate(
            status=status,
            notes=notes,
        )
        
        package = await package_service.update_status(package_uuid, status_update, user)
        
        # Return updated package card (HTMX will swap it)
        return templates.TemplateResponse(
            "packages/status_updated.html",
            {
                "request": request,
                "user": user,
                "package": package,
                "message": f"Status updated to {status}",
            },
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating status: {str(e)}")


@router.post("/{package_id}/photo")
@require_auth
async def add_package_photo(
    request: Request,
    package_id: str,
    photo: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    """
    Add additional photo to package.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        package_id: ID of package to add photo to
        photo: Photo file
        
    Returns:
        Success message with photo information
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        package_uuid = UUID(package_id)
        
        attachment = await package_service.attach_photo(package_uuid, photo, user)
        
        # Return attachment card (HTMX will append it)
        return templates.TemplateResponse(
            "packages/photo_added.html",
            {
                "request": request,
                "user": user,
                "attachment": attachment,
            },
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding photo: {str(e)}")


@router.get("/{package_id}/qrcode/download")
@require_auth
async def download_qr_code(request: Request, package_id: str):
    """
    Download QR code as PNG file.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        package_id: ID of package to generate QR code for
        
    Returns:
        PNG file download with proper Content-Disposition header
    """
    user = get_current_user(request)
    
    try:
        package_uuid = UUID(package_id)
        
        # Verify package exists
        package = await package_service.get_package_by_id(package_uuid)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Generate QR code with configured or fallback URL
        fallback_url = str(request.base_url).rstrip('/')
        base_url = await qrcode_service.get_base_url(fallback_url)
        qr_code_io = qrcode_service.generate_qr_code(package_uuid, base_url)
        
        return Response(
            content=qr_code_io.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=qr_code_{package_id}.png"
            }
        )
    
    except HTTPException as exc:
        # Re-raise HTTP exceptions (e.g., 404) without wrapping
        raise exc
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")


@router.get("/{package_id}/qrcode/print", response_class=HTMLResponse)
@require_auth
async def print_qr_code(request: Request, package_id: str):
    """
    Display print-optimized QR code page.
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        package_id: ID of package to generate QR code for
        
    Returns:
        HTML page with print-optimized QR code view
    """
    user = get_current_user(request)
    
    try:
        package_uuid = UUID(package_id)
        
        # Verify package exists
        package = await package_service.get_package_by_id(package_uuid)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Generate QR code with configured or fallback URL
        fallback_url = str(request.base_url).rstrip('/')
        qr_code_base64 = await qrcode_service.get_qr_code_base64(package_uuid, fallback_url)
        
        return templates.TemplateResponse(
            "packages/qrcode_print.html",
            {
                "request": request,
                "user": user,
                "package": package,
                "qr_code_data": qr_code_base64,
            }
        )
    
    except HTTPException as exc:
        # Re-raise expected HTTP exceptions (e.g., 404) without wrapping
        raise exc
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")
