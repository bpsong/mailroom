"""Admin route package composed from feature-based modules."""

from fastapi import APIRouter, Request

from app.decorators import get_current_user, require_role

from .recipients import router as recipients_router
from .reports import router as reports_router
from .settings import router as settings_router
from .users import router as users_router


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
@require_role("admin")
async def admin_dashboard(request: Request):
    """
    Admin dashboard with system statistics.

    Accessible by: admin, super_admin
    """
    user = get_current_user(request)

    return {
        "message": "Admin dashboard",
        "user": {
            "username": user.username,
            "role": user.role,
        },
    }


router.include_router(users_router)
router.include_router(recipients_router)
router.include_router(settings_router)
router.include_router(reports_router)


__all__ = ["router"]
