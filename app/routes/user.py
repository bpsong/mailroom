"""User self-service routes."""

import logging

from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.templates import templates
from app.decorators import require_auth, get_current_user
from app.middleware.csrf import validate_csrf_token
from app.services.user_service import user_service

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/me", tags=["user"])


@router.get("/profile", response_class=HTMLResponse)
@require_auth
async def profile_page(request: Request):
    """
    Display user profile page with account information.
    
    Accessible by: all authenticated users
    """
    user = get_current_user(request)
    
    # Get user's active sessions
    from app.services.auth_service import auth_service
    sessions = await auth_service.get_user_sessions(user.id)
    
    return templates.TemplateResponse(
        "user/profile.html",
        {
            "request": request,
            "user": user,
            "active_sessions": sessions,
        },
    )


@router.get("/sessions", response_class=HTMLResponse)
@require_auth
async def sessions_page(request: Request):
    """
    Display user's active sessions.
    
    Accessible by: all authenticated users
    """
    user = get_current_user(request)
    
    # Get user's active sessions
    from app.services.auth_service import auth_service
    sessions = await auth_service.get_user_sessions(user.id)
    
    return templates.TemplateResponse(
        "user/sessions.html",
        {
            "request": request,
            "user": user,
            "sessions": sessions,
        },
    )


@router.post("/sessions/{session_id}/terminate")
@require_auth
async def terminate_session(
    request: Request,
    session_id: str,
    csrf_token: str = Form(...),
):
    """
    Terminate a specific session.
    
    Accessible by: all authenticated users (can only terminate own sessions)
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Get session to verify ownership
    from app.services.auth_service import auth_service
    from uuid import UUID
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )
    
    # Terminate the session
    success = await auth_service.terminate_session_by_id(session_uuid, user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already terminated",
        )
    
    return RedirectResponse(
        url="/me/sessions",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/force-password-change", response_class=HTMLResponse)
async def force_password_change_page(request: Request):
    """
    Render forced password change form (for first login or admin reset).
    
    Note: This route doesn't use @require_auth because the user needs to
    change password before full authentication is granted.
    """
    # Check if user has a session but needs password change
    from app.services.auth_service import auth_service
    
    session_token = request.cookies.get("session_token")
    if not session_token:
        logger.debug("Force password change page hit with no session cookie; redirecting to login")
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    session_data = await auth_service.validate_session(session_token)
    if not session_data:
        logger.debug("Invalid session token on force password change page; redirecting to login")
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    session, user = session_data
    
    # If user doesn't need to change password, redirect to dashboard
    if not user.must_change_password:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "user/force_password_change.html",
        {
            "request": request,
            "user": user,
            "error": None,
        },
    )


@router.post("/force-password-change")
async def force_password_change_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(..., min_length=12),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    """
    Process forced password change.
    """
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Get user from session
    from app.services.auth_service import auth_service
    
    session_token = request.cookies.get("session_token")
    if not session_token:
        logger.debug("Force password change submit called without session cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    session_data = await auth_service.validate_session(session_token)
    if not session_data:
        logger.debug("Force password change submit received invalid session token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )
    
    session, user = session_data
    
    # Verify passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "user/force_password_change.html",
            {
                "request": request,
                "user": user,
                "error": "New password and confirmation do not match",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Change password
        await user_service.change_own_password(
            user_id=user.id,
            current_password=current_password,
            new_password=new_password,
        )
        logger.debug("Forced password change successful for user '%s'", user.username)
        
        # Redirect to dashboard
        return RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "user/force_password_change.html",
            {
                "request": request,
                "user": user,
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/password", response_class=HTMLResponse)
@require_auth
async def change_password_page(request: Request):
    """
    Render password change form.
    
    Accessible by: all authenticated users
    """
    user = get_current_user(request)
    
    return templates.TemplateResponse(
        "user/change_password.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/password")
@require_auth
async def change_own_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(..., min_length=12),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    """
    Change own password (self-service).
    
    Accessible by: all authenticated users (operator, admin, super_admin)
    
    Args:
        request: FastAPI request object
        current_password: Current password for verification
        new_password: New password
        confirm_password: Confirmation of new password
        
    Returns:
        Success message
    """
    user = get_current_user(request)
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Verify passwords match
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )
    
    try:
        # Change password
        await user_service.change_own_password(
            user_id=user.id,
            current_password=current_password,
            new_password=new_password,
        )
        
        # Redirect to dashboard
        return RedirectResponse(
            url="/dashboard",
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
            detail=f"Failed to change password: {str(e)}",
        )
