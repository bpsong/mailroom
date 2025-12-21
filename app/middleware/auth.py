"""Authentication middleware for validating sessions."""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate session cookies and inject user into request state."""
    
    # Routes that don't require authentication
    PUBLIC_ROUTES = {
        "/auth/login",
        "/auth/logout",
        "/me/force-password-change",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Routes that start with these prefixes are public
    PUBLIC_PREFIXES = (
        "/static/",
        "/favicon.ico",
    )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate authentication.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler
            
        Returns:
            Response from next handler or redirect to login
        """
        # Check if route is public
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Get session token from cookie
        session_token = request.cookies.get("session_token")
        if session_token:
            logger.debug(
                "Session cookie detected for path %s token_prefix=%s",
                request.url.path,
                session_token[:8],
            )
        if not session_token:
            logger.debug(
                "No session token found for path %s; treating as unauthenticated",
                request.url.path,
            )
            return self._handle_unauthenticated(request)
        
        # Validate session
        session_data = await auth_service.validate_session(session_token)
        
        if not session_data:
            logger.debug(
                "Invalid session token for path %s token_prefix=%s; redirecting to login",
                request.url.path,
                session_token[:8],
            )
            return self._handle_unauthenticated(request)
        
        session, user = session_data
        
        # Inject user into request state
        request.state.user = user
        request.state.session = session
        
        # Check if user must change password (except on password change routes)
        if user.must_change_password and not request.url.path.startswith("/me/force-password-change"):
            # Redirect to forced password change page
            logger.debug(
                "User %s must change password; redirecting to /me/force-password-change",
                getattr(user, "username", "unknown"),
            )
            return RedirectResponse(url="/me/force-password-change", status_code=302)
        
        # Renew session on activity
        await auth_service.renew_session(session_token)
        
        # Continue to next handler
        response = await call_next(request)
        
        return response
    
    def _is_public_route(self, path: str) -> bool:
        """
        Check if a route is public (doesn't require authentication).
        
        Args:
            path: Request path
            
        Returns:
            True if route is public, False otherwise
        """
        # Check exact matches
        if path in self.PUBLIC_ROUTES:
            return True
        
        # Check prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _handle_unauthenticated(self, request: Request) -> Response:
        """
        Handle unauthenticated requests.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Redirect to login for HTML requests, 401 for API requests
        """
        # Check if request expects JSON (API request)
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header or request.url.path.startswith("/api/"):
            logger.debug(
                "Returning 401 JSON for unauthenticated API request to %s",
                request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                    }
                },
            )
        
        # Redirect to login page for HTML requests with next parameter
        from urllib.parse import quote
        next_url = quote(str(request.url.path))
        if request.url.query:
            next_url += quote(f"?{request.url.query}", safe="?=&")
        
        login_url = f"/auth/login?next={next_url}"
        logger.debug(
            "Redirecting unauthenticated browser request from %s to %s",
            request.url.path,
            login_url,
        )
        return RedirectResponse(url=login_url, status_code=302)
