"""Request security helpers."""

from urllib.parse import urlsplit

from fastapi import Request

from app.config import settings


def get_client_ip(request: Request) -> str | None:
    """Return client IP, trusting forwarded headers only from configured proxies."""
    direct_ip = request.client.host if request.client else None

    if direct_ip and direct_ip in settings.trusted_proxy_ips_list:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

    return direct_ip


def safe_redirect_path(path: str | None, default: str = "/dashboard") -> str:
    """Allow only same-origin absolute paths for post-auth redirects."""
    if not path:
        return default

    if path in {"/login", "/auth/login"}:
        return default

    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        return default

    if not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return default

    if "\\" in parsed.path:
        return default

    return path
