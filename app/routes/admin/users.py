"""Admin user management routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.decorators import get_current_user, require_role
from app.middleware.csrf import validate_csrf_token
from app.models import UserCreate
from app.services.rbac_service import rbac_service
from app.services.user_service import user_service
from app.templates import templates
from app.utils.query_params import normalize_optional_bool_param


router = APIRouter()


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
    """Render user list page with search and filtering."""
    user = get_current_user(request)

    is_active_filter, normalized_is_active = normalize_optional_bool_param(
        is_active,
        param_name="is_active",
    )

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
    """Render user creation form."""
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
    """Render user edit form."""
    actor = get_current_user(request)

    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this user",
        )

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
    """Create a new user."""
    actor = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    if not rbac_service.can_create_user_with_role(actor, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to create users with role '{role}'",
        )

    user_data = UserCreate(
        username=username,
        password=password,
        full_name=full_name,
        role=role,
    )

    try:
        await user_service.create_user(user_data, actor)
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
    """Edit an existing user."""
    actor = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this user",
        )

    if role and role != target_user.role:
        if not rbac_service.can_modify_user_field(actor, target_user, "role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to change user roles",
            )

        if not rbac_service.can_create_user_with_role(actor, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to assign role '{role}'",
            )

    try:
        await user_service.update_user(
            user_id=target_user_id,
            full_name=full_name,
            role=role,
            actor=actor,
        )
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
    """Deactivate a user account."""
    actor = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to deactivate this user",
        )

    if actor.id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    try:
        await user_service.deactivate_user(target_user_id, actor)
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
    """Reset a user's password."""
    actor = get_current_user(request)

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    target_user = await user_service.get_user_by_id(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not rbac_service.can_manage_user(actor, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reset this user's password",
        )

    try:
        await user_service.reset_user_password(
            user_id=target_user_id,
            new_password=new_password,
            force_change=force_change,
            actor=actor,
        )
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
