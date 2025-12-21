"""CSRF protection middleware."""

import secrets
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against Cross-Site Request Forgery attacks."""
    
    # HTTP methods that require CSRF validation
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Routes that are exempt from CSRF validation
    EXEMPT_ROUTES = {
        "/health",
    }
    
    # Routes that start with these prefixes are exempt
    EXEMPT_PREFIXES = (
        "/static/",
        "/uploads/",
        "/docs",
        "/redoc",
        "/openapi.json",
    )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate CSRF token for state-changing requests.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler
            
        Returns:
            Response from next handler or 403 if CSRF validation fails
        """
        # Skip CSRF validation for exempt routes
        if self._is_exempt_route(request.url.path):
            response = await call_next(request)
            return response
        
        # Skip CSRF validation for safe methods
        if request.method not in self.PROTECTED_METHODS:
            # Ensure a token is available for templates during safe requests
            if not self._is_exempt_route(request.url.path):
                self._ensure_request_csrf_token(request)
            response = await call_next(request)
            # Add CSRF token to response for safe methods
            if not self._is_exempt_route(request.url.path):
                csrf_token = self._get_request_csrf_token(request)
                if csrf_token:
                    self._set_csrf_cookie(response, csrf_token)
            return response
        
        # Validate CSRF token for protected methods
        if not self._validate_csrf_token(request):
            # Check if this is a browser request (not AJAX/API)
            accept_header = request.headers.get("accept", "")
            is_browser_request = "text/html" in accept_header and "application/json" not in accept_header
            
            if is_browser_request:
                # Redirect to login for browser requests (likely session expired)
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/auth/login", status_code=303)
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token validation failed",
                    }
                },
            )
        
        # Continue to next handler
        response = await call_next(request)
        
        # If route relied on form validation, ensure it occurred
        if getattr(request.state, "csrf_requires_form_validation", False) and not getattr(request.state, "csrf_form_validated", False):
            # Check if this is a browser request (not AJAX/API)
            accept_header = request.headers.get("accept", "")
            is_browser_request = "text/html" in accept_header and "application/json" not in accept_header
            
            if is_browser_request:
                # Redirect to login for browser requests (likely session expired)
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/auth/login", status_code=303)
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_VALIDATION_REQUIRED",
                        "message": "CSRF form token was not validated",
                    }
                },
            )
        
        # Refresh CSRF cookie after successful protected requests
        if not self._is_exempt_route(request.url.path):
            csrf_token = self._get_request_csrf_token(request)
            if csrf_token:
                self._set_csrf_cookie(response, csrf_token)
        
        return response
    
    def _is_exempt_route(self, path: str) -> bool:
        """
        Check if a route is exempt from CSRF validation.
        
        Args:
            path: Request path
            
        Returns:
            True if route is exempt, False otherwise
        """
        # Check exact matches
        if path in self.EXEMPT_ROUTES:
            return True
        
        # Check prefixes
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _get_or_create_csrf_token(self, request: Request) -> str:
        """
        Get existing CSRF token from session or create a new one.
        
        Args:
            request: FastAPI request object
            
        Returns:
            CSRF token string
        """
        # Try to get existing token from session state
        if hasattr(request.state, "session") and hasattr(request.state.session, "csrf_token"):
            token = request.state.session.csrf_token
            request.state.csrf_token = token
            return token
        
        # Try to get from cookie
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token:
            request.state.csrf_token = csrf_token
            return csrf_token
        
        # Generate new token
        csrf_token = secrets.token_urlsafe(32)
        request.state.csrf_token = csrf_token
        return csrf_token
    
    def _ensure_request_csrf_token(self, request: Request) -> str:
        """Ensure request has CSRF token stored on state."""
        token = self._get_request_csrf_token(request)
        if token:
            return token
        return self._get_or_create_csrf_token(request)
    
    def _get_request_csrf_token(self, request: Request) -> str | None:
        """Get CSRF token stored on the request state."""
        return getattr(request.state, "csrf_token", None)
    
    def _set_csrf_cookie(self, response: Response, token: str) -> None:
        """Set CSRF cookie on response."""
        response.set_cookie(
            key="csrf_token",
            value=token,
            httponly=False,  # JavaScript needs to read this
            secure=settings.is_production,  # Only secure in production
            samesite="strict",
            max_age=None,  # Session cookie
        )
    
    def _validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if token is valid, False otherwise
        """
        # Get token from cookie
        cookie_token = request.cookies.get("csrf_token")
        if not cookie_token:
            return False
        
        # Store for downstream usage
        request.state.csrf_token = cookie_token
        
        # Get token from header (for AJAX/HTMX requests)
        header_token = request.headers.get("X-CSRF-Token")
        
        # Validate token from header
        if header_token:
            is_valid = secrets.compare_digest(cookie_token, header_token)
            if is_valid:
                request.state.csrf_requires_form_validation = False
                request.state.csrf_form_validated = True
            return is_valid
        
        # For form submissions, we can't consume the body in middleware
        # Store the expected token in request state for route-level validation
        request.state.csrf_requires_form_validation = True
        request.state.csrf_form_validated = False
        
        # Allow request to proceed; route must call validate_csrf_token()
        return True


def generate_csrf_token() -> str:
    """
    Generate a new CSRF token.
    
    Returns:
        CSRF token string
    """
    return secrets.token_urlsafe(32)


def validate_csrf_token(request: Request, form_token: str = None) -> bool:
    """
    Validate CSRF token from form data.
    
    Args:
        request: FastAPI request object
        form_token: CSRF token from form data
        
    Returns:
        True if token is valid, False otherwise
    """
    if not form_token:
        setattr(request.state, "csrf_form_validated", False)
        return False
    
    expected_token = getattr(request.state, "csrf_token", None)
    if not expected_token:
        expected_token = request.cookies.get("csrf_token")
    
    if not expected_token:
        setattr(request.state, "csrf_form_validated", False)
        return False
    
    is_valid = secrets.compare_digest(expected_token, form_token)
    setattr(request.state, "csrf_form_validated", is_valid)
    if is_valid:
        setattr(request.state, "csrf_requires_form_validation", False)
    return is_valid
