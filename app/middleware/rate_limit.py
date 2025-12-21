"""Rate limiting middleware."""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self):
        """Initialize rate limiter with empty storage."""
        # Storage: {(ip, endpoint): [(timestamp, count), ...]}
        self._requests: Dict[Tuple[str, str], list] = defaultdict(list)
        self._cleanup_interval = 60  # Cleanup old entries every 60 seconds
        self._last_cleanup = time.time()
    
    def is_allowed(self, ip: str, endpoint: str, limit: int, window: int = 60) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            ip: Client IP address
            endpoint: Request endpoint
            limit: Maximum requests allowed in window
            window: Time window in seconds (default 60)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        key = (ip, endpoint)
        
        # Cleanup old entries periodically
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(now, window)
            self._last_cleanup = now
        
        # Get requests for this key
        requests = self._requests[key]
        
        # Remove requests outside the window
        cutoff = now - window
        requests = [req for req in requests if req > cutoff]
        self._requests[key] = requests
        
        # Check if limit exceeded
        if len(requests) >= limit:
            return False
        
        # Add current request
        requests.append(now)
        
        return True
    
    def _cleanup_old_entries(self, now: float, window: int):
        """
        Remove old entries from storage.
        
        Args:
            now: Current timestamp
            window: Time window in seconds
        """
        cutoff = now - window
        keys_to_delete = []
        
        for key, requests in self._requests.items():
            # Remove old requests
            requests = [req for req in requests if req > cutoff]
            if requests:
                self._requests[key] = requests
            else:
                keys_to_delete.append(key)
        
        # Delete empty keys
        for key in keys_to_delete:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API endpoints."""
    
    # Routes with specific rate limits
    ROUTE_LIMITS = {
        "/auth/login": settings.rate_limit_login,  # 10 requests/minute
    }
    
    # Default rate limit for all other routes
    DEFAULT_LIMIT = settings.rate_limit_api  # 100 requests/minute
    
    # Routes exempt from rate limiting
    EXEMPT_ROUTES = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Routes that start with these prefixes are exempt
    EXEMPT_PREFIXES = (
        "/static/",
        "/uploads/",
    )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enforce rate limits.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler
            
        Returns:
            Response from next handler or 429 if rate limit exceeded
        """
        # Skip rate limiting for exempt routes
        if self._is_exempt_route(request.url.path):
            return await call_next(request)
        
        # Get client IP
        ip = self._get_client_ip(request)
        
        # Get rate limit for this route
        limit = self.ROUTE_LIMITS.get(request.url.path, self.DEFAULT_LIMIT)
        
        # Check rate limit
        if not rate_limiter.is_allowed(ip, request.url.path, limit):
            return self._rate_limit_exceeded_response(limit)
        
        # Continue to next handler
        response = await call_next(request)
        
        return response
    
    def _is_exempt_route(self, path: str) -> bool:
        """
        Check if a route is exempt from rate limiting.
        
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
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Use direct client IP
        return request.client.host if request.client else "unknown"
    
    def _rate_limit_exceeded_response(self, limit: int) -> Response:
        """
        Create response for rate limit exceeded.
        
        Args:
            limit: Rate limit that was exceeded
            
        Returns:
            429 Too Many Requests response
        """
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
                }
            },
            headers={
                "Retry-After": "60",  # Retry after 60 seconds
            },
        )
