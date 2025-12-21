"""Authentication routes for login and logout."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse

from app.templates import templates
from app.services.auth_service import auth_service
from app.database.connection import get_db
from app.middleware.csrf import validate_csrf_token
from app.config import settings

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["authentication"])


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: Optional[str] = None):
    """
    Display login page.
    
    If user is already authenticated, redirect to dashboard or next URL.
    
    Args:
        request: FastAPI request object
        next: Optional URL to redirect to after login
        
    Returns:
        Login page HTML
    """
    # Check if user is already authenticated
    session_token = request.cookies.get("session_token")
    if session_token:
        session_data = await auth_service.validate_session(session_token)
        if session_data:
            # User is authenticated, redirect to next URL or dashboard
            redirect_url = next if next else "/dashboard"
            logger.debug("Authenticated session detected on login page; redirecting to %s", redirect_url)
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    
    # Render login page
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "error": None,
            "next": next,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: Optional[str] = Form(None),
):
    """
    Authenticate user and create session.
    
    Args:
        request: FastAPI request object
        username: Username from form
        password: Password from form
        csrf_token: CSRF token from form
        next: Optional URL to redirect to after login
        
    Returns:
        Redirect to next URL or dashboard on success, error response on failure
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    logger.debug(
        "Login attempt for user '%s' from ip=%s ua=%s",
        username,
        ip_address,
        user_agent,
    )
    
    # Validate CSRF token
    if not validate_csrf_token(request, csrf_token):
        logger.warning("CSRF validation failed for login attempt user='%s'", username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Check if account is locked
    is_locked, locked_until = await auth_service.check_account_lockout(username)
    if is_locked:
        # Log failed login attempt
        await auth_service.log_auth_event(
            event_type="login_failed",
            username=username,
            ip_address=ip_address,
            details=json.dumps({"reason": "account_locked", "locked_until": str(locked_until)}),
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {locked_until}. Please try again later.",
        )
    
    # Get user from database
    db = get_db()
    with db.get_read_connection() as conn:
        result = conn.execute(
            """
            SELECT id, username, password_hash, full_name, role, is_active,
                   must_change_password, password_history, failed_login_count,
                   locked_until, created_at, updated_at
            FROM users
            WHERE username = ?
            """,
            [username],
        ).fetchone()
    
    if not result:
        # Log failed login attempt
        await auth_service.log_auth_event(
            event_type="login_failed",
            username=username,
            ip_address=ip_address,
            details=json.dumps({"reason": "invalid_username"}),
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Parse user data
    from app.models import User
    user = User(
        id=result[0],
        username=result[1],
        password_hash=result[2],
        full_name=result[3],
        role=result[4],
        is_active=result[5],
        must_change_password=result[6],
        password_history=result[7],
        failed_login_count=result[8],
        locked_until=result[9],
        created_at=result[10],
        updated_at=result[11],
    )
    
    # Check if user is active
    if not user.is_active:
        logger.debug("Inactive user '%s' attempted login", username)
        # Log failed login attempt
        await auth_service.log_auth_event(
            event_type="login_failed",
            username=username,
            ip_address=ip_address,
            details=json.dumps({"reason": "account_inactive"}),
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact an administrator.",
        )
    
    # Verify password
    if not auth_service.verify_password(password, user.password_hash):
        logger.debug("Invalid password for user '%s'", username)
        # Increment failed login counter
        await auth_service.increment_failed_login(username)
        
        # Log failed login attempt
        await auth_service.log_auth_event(
            event_type="login_failed",
            username=username,
            ip_address=ip_address,
            details=json.dumps({"reason": "invalid_password"}),
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Reset failed login counter
    await auth_service.reset_failed_login(username)
    
    # Create session
    session = await auth_service.create_session(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    logger.debug(
        "Session created for user '%s': id=%s token_prefix=%s",
        username,
        session.id,
        session.token[:8],
    )
    
    # Log successful login
    await auth_service.log_auth_event(
        event_type="login",
        user_id=user.id,
        username=username,
        ip_address=ip_address,
        details=json.dumps({"session_id": str(session.id)}),
    )
    
    # Determine redirect URL
    redirect_url = next if next else "/dashboard"
    
    # If user must change password, redirect to force password change page
    if user.must_change_password:
        redirect_url = "/me/force-password-change"
    
    response_payload = {
        "success": True,
        "message": "Login successful",
        "redirect_url": redirect_url,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "must_change_password": user.must_change_password,
        },
    }
    
    response = JSONResponse(response_payload)
    response.set_cookie(
        key="session_token",
        value=session.token,
        httponly=True,
        secure=settings.is_production,  # Only send over HTTPS in production
        samesite="lax",
        path="/",
        max_age=None,  # Session cookie (expires when browser closes)
    )
    
    # Return success response
    logger.debug(
        "Login successful for user '%s'; redirecting to %s; must_change_password=%s",
        username,
        redirect_url,
        user.must_change_password,
    )
    return response


@router.post("/logout")
async def logout(
    request: Request,
    csrf_token: str = Form(...),
):
    """
    Terminate user session and log out.
    
    Note: This endpoint doesn't require @require_auth decorator because
    we want to allow logout even if session is expired or invalid.
    
    Args:
        request: FastAPI request object
        csrf_token: CSRF token from form
        
    Returns:
        Redirect to login page
    """
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Get session token from cookie
    session_token = request.cookies.get("session_token")
    
    if session_token:
        # Validate session to get user info for logging
        session_data = await auth_service.validate_session(session_token)
        
        if session_data:
            session, user = session_data
            
            # Log logout event
            await auth_service.log_auth_event(
                event_type="logout",
                user_id=user.id,
                username=user.username,
                ip_address=get_client_ip(request),
                details=json.dumps({"session_id": str(session.id)}),
            )
        
        # Terminate session
        await auth_service.terminate_session(session_token)
    
    # Create redirect response and clear session cookie
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_token", path="/")
    
    return response


@router.get("/me")
async def get_current_user_info(request: Request):
    """
    Get current authenticated user information.
    
    This endpoint is protected by the authentication middleware,
    so the user will already be injected into request.state.user.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current user information
    """
    # This endpoint will be protected by auth middleware
    # The user will be injected into request.state.user
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    user = request.state.user
    
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "must_change_password": user.must_change_password,
    }
