"""API route handlers."""

from app.routes import admin, auth, dashboard, packages, recipients, user

__all__ = [
    "auth",
    "admin",
    "packages",
    "recipients",
    "dashboard",
    "user",
]
