"""API route handlers."""

from app.routes import auth, admin, packages, recipients, dashboard, user

__all__ = [
    "auth",
    "admin",
    "packages",
    "recipients",
    "dashboard",
    "user",
]
