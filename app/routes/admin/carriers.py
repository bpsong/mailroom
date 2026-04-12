"""Admin carrier management routes."""

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.decorators import get_current_user, require_role
from app.middleware.csrf import validate_csrf_token
from app.models.carrier import CarrierCreate, CarrierUpdate
from app.services.carrier_service import carrier_service


router = APIRouter(prefix="/carriers")


@router.post("")
@require_role("admin", "super_admin")
async def create_carrier(
    request: Request,
    name: str = Form(...),
    csrf_token: str = Form(...),
):
    """Create a new carrier."""
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        await carrier_service.create_carrier(CarrierCreate(name=name))
        return RedirectResponse(
            url="/admin/settings?success=carrier_created",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        error = str(e).replace(" ", "+")
        return RedirectResponse(
            url=f"/admin/settings?error={error}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{carrier_id}/edit")
@require_role("admin", "super_admin")
async def edit_carrier(
    request: Request,
    carrier_id: int,
    name: str = Form(...),
    csrf_token: str = Form(...),
):
    """Update an existing carrier's name."""
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        await carrier_service.update_carrier(carrier_id, CarrierUpdate(name=name))
        return RedirectResponse(
            url="/admin/settings?success=carrier_updated",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        error = str(e).replace(" ", "+")
        return RedirectResponse(
            url=f"/admin/settings?error={error}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{carrier_id}/deactivate")
@require_role("admin", "super_admin")
async def deactivate_carrier(
    request: Request,
    carrier_id: int,
    csrf_token: str = Form(...),
):
    """Deactivate a carrier."""
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    try:
        await carrier_service.deactivate_carrier(carrier_id)
        return RedirectResponse(
            url="/admin/settings?success=carrier_deactivated",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        error = str(e).replace(" ", "+")
        return RedirectResponse(
            url=f"/admin/settings?error={error}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
