"""Security headers middleware."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler
            
        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response) -> None:
        """
        Add security headers to response.
        
        Args:
            response: FastAPI response object
        """
        # Strict-Transport-Security (HSTS)
        # Force HTTPS for 1 year, include subdomains
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # X-Content-Type-Options
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        # Prevent clickjacking by disallowing iframe embedding
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection
        # Enable browser XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        # Control referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content-Security-Policy
        # Restrict resource loading to prevent XSS and other attacks
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://unpkg.com",  # HTMX from CDN
            "style-src 'self' 'unsafe-inline'",  # Inline styles for daisyUI
            "img-src 'self' data: blob:",  # Allow data URIs for images
            "font-src 'self'",
            "connect-src 'self'",  # HTMX AJAX requests
            "frame-ancestors 'none'",  # Same as X-Frame-Options
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Permissions-Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions_directives = [
            "geolocation=()",
            "microphone=()",
            "camera=(self)",  # Allow camera for package photos
            "payment=()",
            "usb=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)
