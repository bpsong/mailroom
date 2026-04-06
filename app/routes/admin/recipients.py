"""Admin recipient management routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.decorators import get_current_user, require_role
from app.middleware.csrf import validate_csrf_token
from app.models import RecipientCreate, RecipientUpdate
from app.services.csv_import_service import csv_import_service
from app.services.recipient_service import recipient_service
from app.templates import templates
from app.utils.query_params import normalize_optional_bool_param


router = APIRouter()


@router.get("/recipients", response_class=HTMLResponse)
@require_role("admin")
async def list_recipients_page(
    request: Request,
    query: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    is_active: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Render recipient list page with search and filtering."""
    user = get_current_user(request)

    is_active_filter, normalized_is_active = normalize_optional_bool_param(
        is_active,
        param_name="is_active",
    )

    recipients, total_count = await recipient_service.list_recipients(
        query=query,
        department=department,
        is_active=is_active_filter,
        limit=limit,
        offset=offset,
    )

    context = {
        "request": request,
        "user": user,
        "recipients": recipients,
        "query": query,
        "department": department,
        "is_active": normalized_is_active,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        },
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("admin/recipients_table_partial.html", context)

    return templates.TemplateResponse("admin/recipients_list.html", context)


@router.get("/recipients/new", response_class=HTMLResponse)
@require_role("admin")
async def create_recipient_page(request: Request):
    """Render recipient creation form."""
    user = get_current_user(request)

    return templates.TemplateResponse(
        "admin/recipient_create.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/recipients/new")
@require_role("admin")
async def create_recipient(
    request: Request,
    employee_id: str = Form(..., min_length=1, max_length=50),
    name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    department: str = Form(..., max_length=100),
    phone: Optional[str] = Form(None, max_length=20),
    location: Optional[str] = Form(None, max_length=100),
    csrf_token: str = Form(...),
):
    """Create a new recipient."""
    get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    recipient_data = RecipientCreate(
        employee_id=employee_id,
        name=name,
        email=email,
        department=department,
        phone=phone,
        location=location,
    )

    try:
        await recipient_service.create_recipient(recipient_data)
        return RedirectResponse(
            url="/admin/recipients",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create recipient: {str(e)}",
        )


@router.get("/recipients/{recipient_id}/edit", response_class=HTMLResponse)
@require_role("admin")
async def edit_recipient_page(request: Request, recipient_id: str):
    """Render recipient edit form."""
    user = get_current_user(request)

    try:
        recipient_uuid = UUID(recipient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient ID format",
        )

    recipient = await recipient_service.get_recipient_by_id(recipient_uuid)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found",
        )

    return templates.TemplateResponse(
        "admin/recipient_edit.html",
        {
            "request": request,
            "user": user,
            "edit_recipient": recipient,
        },
    )


@router.api_route("/recipients/{recipient_id}/edit", methods=["POST", "PUT"])
@require_role("admin")
async def edit_recipient(
    request: Request,
    recipient_id: str,
    name: Optional[str] = Form(None, min_length=1, max_length=100),
    email: Optional[str] = Form(None),
    department: str = Form(..., max_length=100),
    phone: Optional[str] = Form(None, max_length=20),
    location: Optional[str] = Form(None, max_length=100),
    csrf_token: str = Form(...),
):
    """Edit an existing recipient."""
    get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        recipient_uuid = UUID(recipient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient ID format",
        )

    recipient_data = RecipientUpdate(
        name=name,
        email=email,
        department=department,
        phone=phone,
        location=location,
    )

    try:
        await recipient_service.update_recipient(
            recipient_id=recipient_uuid,
            recipient_data=recipient_data,
        )
        return RedirectResponse(
            url=f"/admin/recipients/{recipient_id}/edit",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update recipient: {str(e)}",
        )


@router.post("/recipients/{recipient_id}/deactivate")
@require_role("admin")
async def deactivate_recipient(
    request: Request,
    recipient_id: str,
    csrf_token: str = Form(...),
):
    """Deactivate a recipient."""
    get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        recipient_uuid = UUID(recipient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient ID format",
        )

    try:
        await recipient_service.deactivate_recipient(recipient_uuid)
        return RedirectResponse(
            url="/admin/recipients",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate recipient: {str(e)}",
        )


@router.get("/recipients/import", response_class=HTMLResponse)
@require_role("admin")
async def import_recipients_page(request: Request):
    """Render CSV import page."""
    user = get_current_user(request)

    return templates.TemplateResponse(
        "admin/recipient_import.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/recipients/import/validate")
@require_role("admin")
async def validate_recipients_csv(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    """Validate CSV file in dry-run mode."""
    get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    try:
        content = await file.read()
        result, valid_recipients = await csv_import_service.parse_and_validate_csv(content)
        return JSONResponse(
            content={
                "success": result.error_count == 0,
                "result": result.to_dict(),
                "valid_count": len(valid_recipients),
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate CSV: {str(e)}",
        )


@router.post("/recipients/import/confirm")
@require_role("admin")
async def import_recipients_csv(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    """Import recipients from a validated CSV file."""
    user = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    try:
        content = await file.read()
        validation_result, valid_recipients = await csv_import_service.parse_and_validate_csv(content)

        if validation_result.error_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file contains validation errors. Please fix and try again.",
            )

        import_result = await csv_import_service.import_recipients(
            valid_recipients,
            user,
            filename=file.filename or "import.csv",
        )

        return JSONResponse(
            content={
                "success": True,
                "result": import_result.to_dict(),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import CSV: {str(e)}",
        )
