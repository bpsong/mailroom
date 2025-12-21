"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.migrations import run_initial_migration
from app.database.write_queue import get_write_queue, close_write_queue


def configure_logging() -> None:
    """Configure application logging based on settings."""
    level_name = getattr(settings, "log_level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        force=True,
    )
    # Reduce noisy access logs while keeping debug for application modules.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(level)


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Mailroom Tracking System")
    
    # Initialize database
    try:
        run_initial_migration(create_super_admin=True)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Start write queue
    try:
        await get_write_queue()
        logger.info("Write queue started")
    except Exception as e:
        logger.error(f"Failed to start write queue: {e}")
        raise
    
    # Clean up expired sessions
    try:
        from app.services.auth_service import auth_service
        expired_count = await auth_service.cleanup_expired_sessions()
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions on startup")
    except Exception as e:
        logger.warning(f"Failed to cleanup expired sessions: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mailroom Tracking System")
    
    # Stop write queue
    try:
        await close_write_queue()
        logger.info("Write queue stopped")
    except Exception as e:
        logger.error(f"Error stopping write queue: {e}")


app = FastAPI(
    title="Mailroom Tracking System",
    description="Internal package tracking application",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware (order matters - last added is executed first)
from app.middleware import (
    AuthenticationMiddleware,
    CSRFMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount uploads directory for serving package photos
from pathlib import Path
uploads_dir = Path(settings.upload_dir)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Import shared templates instance
from app.templates import templates

# Include routers
from app.routes import auth, admin, packages, recipients, dashboard, user
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(packages.router)
app.include_router(recipients.router)
app.include_router(dashboard.router)
app.include_router(user.router)


@app.get("/")
async def root():
    """Root endpoint - redirect to login page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auth/login", status_code=302)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns comprehensive health status including:
    - Database connection status
    - Disk space availability
    - Application uptime
    """
    from app.services.health_service import get_health_service
    
    health_service = get_health_service()
    health_status = await health_service.get_full_health_status()
    
    return health_status


# Custom error handlers
from fastapi import Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with appropriate responses."""
    # For API/AJAX requests, return JSON
    if request.headers.get("accept") == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    
    # For HTML requests, use templates for specific status codes
    if exc.status_code == 403:
        return templates.TemplateResponse(
            "errors/403.html",
            {"request": request},
            status_code=status.HTTP_403_FORBIDDEN,
        )
    elif exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # For other HTTP exceptions, return JSON
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle 500 Internal Server Error with custom template."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
