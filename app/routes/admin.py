"""Admin routes for user and recipient management."""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

from app.templates import templates
from app.decorators import require_role, get_current_user
from app.routes.auth import get_client_ip
from app.middleware.csrf import validate_csrf_token
from app.services.rbac_service import rbac_service
from app.services.user_service import user_service
from app.services.recipient_service import recipient_service
from app.services.csv_import_service import csv_import_service
from app.models import UserCreate, RecipientCreate, RecipientUpdate
from app.utils.query_params import normalize_optional_bool_param


router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response models
class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(super_admin|admin|operator)$")


class PasswordResetRequest(BaseModel):
    """Request model for resetting a user's password."""
    new_password: str = Field(..., min_length=12)
    force_change: bool = True


@router.get("/dashboard")
@require_role("admin")
async def admin_dashboard(request: Request):
    """
    Admin dashboard with system statistics.
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dashboard data
    """
    user = get_current_user(request)
    
    return {
        "message": "Admin dashboard",
        "user": {
            "username": user.username,
            "role": user.role,
        },
    }


@router.get("/users", response_class=HTMLResponse)
@require_role("admin")
async def list_users_page(
    request: Request,
    query: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Render user list page with search and filtering.
    
    Accessible by: admin, super_admin
    """
    user = get_current_user(request)
    
    is_active_filter, normalized_is_active = normalize_optional_bool_param(
        is_active,
        param_name="is_active",
    )
    
    # Search users
    users, total_count = await user_service.search_users(
        query=query,
        role=role,
        is_active=is_active_filter,
        limit=limit,
        offset=offset,
    )
    
    return templates.TemplateResponse(
        "admin/users_list.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "query": query,
            "role": role,
            "is_active": normalized_is_active,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
        },
    )


@router.get("/users/new", response_class=HTMLResponse)
@require_role("admin")
async def create_user_page(request: Request):
    """
    Render user creation form.
    
    Accessible by: admin, super_admin
    """
    user = get_current_user(request)
    
    return templates.TemplateResponse(
        "admin/user_create.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
@require_role("admin")
async def edit_user_page(request: Request, user_id: str):
    """
    Render user edit form.
    
    Accessible by: admin, super_admin
    """
    actor = get_current_user(request)
    
    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    # Get target user
    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if actor can manage target user
    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this user",
        )
    
    # Check if actor can change role
    can_change_role = rbac_service.can_modify_user_field(actor, target_user, "role")
    
    return templates.TemplateResponse(
        "admin/user_edit.html",
        {
            "request": request,
            "user": actor,
            "edit_user": target_user,
            "can_change_role": can_change_role,
        },
    )





@router.post("/users/new")
@require_role("admin")
async def create_user(
    request: Request,
    username: str = Form(..., min_length=3, max_length=50),
    password: str = Form(..., min_length=12),
    full_name: str = Form(..., min_length=1, max_length=100),
    role: str = Form(..., pattern="^(super_admin|admin|operator)$"),
    csrf_token: str = Form(...),
):
    """
    Create a new user.
    
    Accessible by: admin, super_admin
    Note: Admins can only create operators, super_admins can create any role
    
    Args:
        request: FastAPI request object
        username: Username for new user
        password: Initial password
        full_name: Full name of user
        role: Role for new user
        
    Returns:
        Created user information
    """
    actor = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Check if actor can create user with this role
    if not rbac_service.can_create_user_with_role(actor, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to create users with role '{role}'",
        )
    
    # Create user data
    user_data = UserCreate(
        username=username,
        password=password,
        full_name=full_name,
        role=role,
    )
    
    try:
        # Create user
        new_user = await user_service.create_user(user_data, actor)
        
        # Redirect to user list
        return RedirectResponse(
            url="/admin/users",
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
            detail=f"Failed to create user: {str(e)}",
        )


@router.put("/users/{user_id}/edit")
@require_role("admin")
async def edit_user(
    request: Request,
    user_id: str,
    full_name: Optional[str] = Form(None, min_length=1, max_length=100),
    role: Optional[str] = Form(None, pattern="^(super_admin|admin|operator)$"),
    csrf_token: str = Form(...),
):
    """
    Edit an existing user.
    
    Accessible by: admin, super_admin
    Note: Admins can only edit operators, super_admins can edit anyone
    
    Args:
        request: FastAPI request object
        user_id: ID of user to edit
        full_name: New full name (optional)
        role: New role (optional)
        
    Returns:
        Updated user information
    """
    actor = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        # Parse user_id
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    # Get target user
    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if actor can manage target user
    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this user",
        )
    
    # Check if role change is allowed
    if role and role != target_user.role:
        if not rbac_service.can_modify_user_field(actor, target_user, "role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to change user roles",
            )
        
        # Check if actor can create users with the new role
        if not rbac_service.can_create_user_with_role(actor, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to assign role '{role}'",
            )
    
    try:
        # Update user
        updated_user = await user_service.update_user(
            user_id=target_user_id,
            full_name=full_name,
            role=role,
            actor=actor,
        )
        
        # Redirect back to edit page
        return RedirectResponse(
            url=f"/admin/users/{user_id}/edit",
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
            detail=f"Failed to update user: {str(e)}",
        )


@router.post("/users/{user_id}/deactivate")
@require_role("admin")
async def deactivate_user(
    request: Request,
    user_id: str,
    csrf_token: str = Form(...),
):
    """
    Deactivate a user account.
    
    Accessible by: admin, super_admin
    Note: Admins can only deactivate operators, super_admins can deactivate anyone
    
    Args:
        request: FastAPI request object
        user_id: ID of user to deactivate
        
    Returns:
        Success message
    """
    actor = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        # Parse user_id
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    # Get target user
    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if actor can manage target user
    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to deactivate this user",
        )
    
    # Prevent self-deactivation
    if actor.id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    
    try:
        # Deactivate user
        await user_service.deactivate_user(target_user_id, actor)
        
        # Redirect to user list
        return RedirectResponse(
            url="/admin/users",
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
            detail=f"Failed to deactivate user: {str(e)}",
        )


@router.post("/users/{user_id}/password")
@require_role("admin")
async def reset_user_password(
    request: Request,
    user_id: str,
    new_password: str = Form(..., min_length=12),
    force_change: bool = Form(True),
    csrf_token: str = Form(...),
):
    """
    Reset a user's password (admin function).
    
    Accessible by: admin, super_admin
    Note: Admins can only reset passwords for operators
    
    Args:
        request: FastAPI request object
        user_id: ID of user whose password to reset
        new_password: New password for the user
        force_change: Whether to require password change on next login
        
    Returns:
        Success message
    """
    actor = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    try:
        # Parse user_id
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    # Get target user
    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if actor can manage target user
    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reset this user's password",
        )
    
    try:
        # Reset password
        await user_service.reset_user_password(
            user_id=target_user_id,
            new_password=new_password,
            force_change=force_change,
            actor=actor,
        )
        
        # Redirect back to edit page
        return RedirectResponse(
            url=f"/admin/users/{user_id}/edit",
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
            detail=f"Failed to reset password: {str(e)}",
        )


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
    """
    Render recipient list page with search and filtering.
    
    Accessible by: admin, super_admin
    """
    user = get_current_user(request)
    
    is_active_filter, normalized_is_active = normalize_optional_bool_param(
        is_active,
        param_name="is_active",
    )
    
    # Search recipients
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
    
    # Check if this is an HTMX request (for pagination)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "admin/recipients_table_partial.html",
            context,
        )
    
    return templates.TemplateResponse(
        "admin/recipients_list.html",
        context,
    )


@router.get("/recipients/new", response_class=HTMLResponse)
@require_role("admin")
async def create_recipient_page(request: Request):
    """
    Render recipient creation form.
    
    Accessible by: admin, super_admin
    """
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
    """
    Create a new recipient.
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        employee_id: Unique employee ID
        name: Full name of recipient
        email: Email address
        department: Department (optional)
        phone: Phone number (optional)
        location: Location (optional)
        
    Returns:
        Redirect to recipient list
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Create recipient data
    recipient_data = RecipientCreate(
        employee_id=employee_id,
        name=name,
        email=email,
        department=department,
        phone=phone,
        location=location,
    )
    
    try:
        # Create recipient
        new_recipient = await recipient_service.create_recipient(recipient_data)
        
        # Redirect to recipient list
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
    """
    Render recipient edit form.
    
    Accessible by: admin, super_admin
    """
    user = get_current_user(request)
    
    try:
        recipient_uuid = UUID(recipient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient ID format",
        )
    
    # Get recipient
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
    """
    Edit an existing recipient.
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        recipient_id: ID of recipient to edit
        name: New name (optional)
        email: New email (optional)
        department: New department (optional)
        phone: New phone (optional)
        location: New location (optional)
        
    Returns:
        Redirect to edit page
    """
    user = get_current_user(request)
    
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
    
    # Create update data
    recipient_data = RecipientUpdate(
        name=name,
        email=email,
        department=department,
        phone=phone,
        location=location,
    )
    
    try:
        # Update recipient
        updated_recipient = await recipient_service.update_recipient(
            recipient_id=recipient_uuid,
            recipient_data=recipient_data,
        )
        
        # Redirect back to edit page
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
    """
    Deactivate a recipient.
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        recipient_id: ID of recipient to deactivate
        
    Returns:
        Redirect to recipient list
    """
    user = get_current_user(request)
    
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
        # Deactivate recipient
        await recipient_service.deactivate_recipient(recipient_uuid)
        
        # Redirect to recipient list
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
    """
    Render CSV import page.
    
    Accessible by: admin, super_admin
    """
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
    """
    Validate CSV file (dry-run mode).
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        file: Uploaded CSV file
        
    Returns:
        Validation results
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Check file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse and validate
        result, valid_recipients = await csv_import_service.parse_and_validate_csv(content)
        
        # Return validation results
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
    """
    Import recipients from CSV file (after validation).
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        file: Uploaded CSV file
        
    Returns:
        Import results
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Check file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse and validate
        validation_result, valid_recipients = await csv_import_service.parse_and_validate_csv(content)
        
        # Check for validation errors
        if validation_result.error_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file contains validation errors. Please fix and try again.",
            )
        
        # Import recipients
        import_result = await csv_import_service.import_recipients(
            valid_recipients, 
            user,
            filename=file.filename or "import.csv"
        )
        
        # Return import results
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


@router.get("/reports", response_class=HTMLResponse)
@require_role("admin")
async def reports_page(request: Request):
    """
    Render reports page with filters and export functionality.
    
    Accessible by: admin, super_admin
    """
    from app.services.dashboard_service import dashboard_service
    from app.services.user_service import user_service
    
    user = get_current_user(request)
    
    # Get filter options
    departments = await dashboard_service.get_department_list()
    operators, _ = await user_service.search_users(role="operator", is_active=True, limit=100, offset=0)
    
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
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recipient_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
):
    """
    Preview packages that match the report filters.
    
    Accessible by: admin, super_admin
    """
    from datetime import datetime
    from app.models import PackageFilters, Pagination
    from app.services.package_service import package_service
    
    user = get_current_user(request)
    
    # Parse date parameters
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
    
    # Parse UUID parameters
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
    
    # Build filters
    filters = PackageFilters(
        query=query,
        status=status,
        department=department,
        date_from=date_from_dt,
        date_to=date_to_dt,
        recipient_id=recipient_uuid,
        created_by=created_by_uuid,
    )
    
    # Get preview (first 10 packages)
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
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recipient_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
):
    """
    Export packages report as CSV with filters.
    
    Accessible by: admin, super_admin
    
    Args:
        request: FastAPI request object
        query: Search query for tracking_no or recipient name
        status: Filter by package status
        department: Filter by recipient department
        date_from: Filter packages created from this date (ISO format)
        date_to: Filter packages created until this date (ISO format)
        recipient_id: Filter by specific recipient UUID
        created_by: Filter by operator who created the package UUID
        
    Returns:
        CSV file download
    """
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    from app.services.export_service import export_service
    
    user = get_current_user(request)
    
    # Parse date parameters
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
    
    # Parse UUID parameters
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
        # Generate CSV
        csv_content = await export_service.export_packages_csv(
            query=query,
            status=status,
            department=department,
            date_from=date_from_dt,
            date_to=date_to_dt,
            recipient_id=recipient_uuid,
            created_by=created_by_uuid,
        )
        
        # Create streaming response
        output = BytesIO(csv_content.encode('utf-8'))
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"packages_export_{timestamp}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export packages: {str(e)}",
        )


@router.get("/settings", response_class=HTMLResponse)
@require_role("super_admin")
async def show_settings(request: Request):
    """
    Display system settings page (Super Admin only).
    
    Accessible by: super_admin only
    
    Args:
        request: FastAPI request object
        
    Returns:
        System settings page
    """
    from app.services.system_settings_service import system_settings_service
    
    user = get_current_user(request)
    
    # Get current QR base URL
    qr_base_url = await system_settings_service.get_qr_base_url()
    
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": user,
            "qr_base_url": qr_base_url or "",
        }
    )


@router.post("/settings/qr-base-url")
@require_role("super_admin")
async def update_qr_base_url(
    request: Request,
    qr_base_url: str = Form(...),
    csrf_token: str = Form(...),
):
    """
    Update QR code base URL (Super Admin only).
    
    Accessible by: super_admin only
    
    Args:
        request: FastAPI request object
        qr_base_url: New base URL for QR codes
        csrf_token: CSRF token for validation
        
    Returns:
        Settings page with success/error message
    """
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
        
        return templates.TemplateResponse(
            "admin/settings.html",
            {
                "request": request,
                "user": user,
                "qr_base_url": qr_base_url,
                "success": "QR code base URL updated successfully",
            }
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "admin/settings.html",
            {
                "request": request,
                "user": user,
                "qr_base_url": qr_base_url,
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
    """
    View audit logs with filtering and pagination (super admin only).
    
    Accessible by: super_admin only
    
    Args:
        request: FastAPI request object
        user_id: Filter by user ID
        event_type: Filter by event type
        username: Filter by username (partial match)
        start_date: Filter events after this date (ISO format)
        end_date: Filter events before this date (ISO format)
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        Audit log list page
    """
    from datetime import datetime
    from app.services.audit_service import audit_service
    
    user = get_current_user(request)
    
    # Parse date parameters
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
    
    # Parse user_id
    user_uuid = None
    if user_id:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            pass
    
    # Get audit events
    events, total_count = await audit_service.get_auth_events(
        user_id=user_uuid,
        event_type=event_type,
        username=username,
        start_date=start_date_dt,
        end_date=end_date_dt,
        limit=limit,
        offset=offset,
    )
    
    # Get unique event types for filter dropdown
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
    
    # Check if this is an HTMX request (for search/filter)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "admin/audit_logs_table_partial.html",
            context,
        )
    
    return templates.TemplateResponse(
        "admin/audit_logs.html",
        context,
    )
