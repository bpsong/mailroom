"""Template helper functions."""

from typing import Optional

from fastapi import Request
from jinja2 import pass_context
from markupsafe import Markup

from app.middleware.csrf import generate_csrf_token


def get_csrf_token(request: Request) -> str:
    """
    Get or generate CSRF token for templates.
    
    Args:
        request: FastAPI request object
        
    Returns:
        CSRF token string
    """
    # Prefer token stored on request state (middleware)
    token = getattr(request.state, "csrf_token", None)
    if token:
        return token
    
    # Try to get from cookie
    csrf_token = request.cookies.get("csrf_token")
    if csrf_token:
        request.state.csrf_token = csrf_token
        return csrf_token
    
    # Generate new token as fallback (ensuring state stores it)
    csrf_token = generate_csrf_token()
    request.state.csrf_token = csrf_token
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


@pass_context
def csrf_token_value(context, request: Optional[Request] = None) -> str:
    """
    Jinja helper: return CSRF token for current request.
    """
    request = request or context.get("request")
    if not request:
        return ""
    return get_csrf_token(request)


@pass_context
def csrf_input(context, request: Optional[Request] = None) -> Markup:
    """
    Jinja helper: render hidden CSRF input element.
    """
    token = csrf_token_value(context, request)
    if not token:
        return Markup("")
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')
