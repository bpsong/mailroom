"""Authentication and authorization decorators."""

from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, status

from app.services.rbac_service import rbac_service


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Args:
        func: Route handler function
        
    Returns:
        Wrapped function that checks authentication
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get request from kwargs
        request = kwargs.get("request")
        if not request:
            # Try to find request in args
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        
        if not request or not hasattr(request.state, "user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to require specific role(s) for a route.
    
    Role hierarchy:
    - super_admin: Has access to all endpoints
    - admin: Has access to admin and operator endpoints
    - operator: Has access only to operator endpoints
    
    Args:
        allowed_roles: One or more role names that are allowed
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request or not hasattr(request.state, "user"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            user = request.state.user
            
            # Super admin has access to everything
            if user.role == "super_admin":
                return await func(*args, **kwargs)
            
            # Admin has access to admin endpoints (but not super_admin only endpoints)
            if user.role == "admin" and "admin" in allowed_roles:
                return await func(*args, **kwargs)
            
            # Check if user's role is explicitly in allowed roles
            if user.role in allowed_roles:
                return await func(*args, **kwargs)
            
            # Access denied
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        
        return wrapper
    
    return decorator


def require_permission(permission: str) -> Callable:
    """
    Decorator to require a specific permission for a route.
    
    This provides more granular control than role-based access.
    
    Args:
        permission: Permission name required
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request or not hasattr(request.state, "user"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            user = request.state.user
            
            # Check if user has the required permission
            if not rbac_service.has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required permission: {permission}",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_current_user(request: Request):
    """
    Helper function to get current authenticated user from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    return request.state.user
