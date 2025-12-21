"""CSRF token helper utilities."""

from fastapi import Request
from app.middleware.csrf import generate_csrf_token


def get_csrf_token(request: Request) -> str:
    """
    Get or generate CSRF token for the request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        CSRF token string
    """
    # Try to get from cookie first
    csrf_token = request.cookies.get("csrf_token")
    
    # If not in cookie, generate new one
    if not csrf_token:
        csrf_token = generate_csrf_token()
    
    return csrf_token


def add_csrf_to_context(request: Request, context: dict) -> dict:
    """
    Add CSRF token to template context.
    
    Args:
        request: FastAPI request object
        context: Template context dictionary
        
    Returns:
        Updated context with csrf_token
    """
    context["csrf_token"] = get_csrf_token(request)
    return context
