"""Tests for request security helper behavior."""

from types import SimpleNamespace

from app.utils.request_security import get_client_ip, safe_redirect_path


class _Request:
    def __init__(self, host: str, headers: dict[str, str] | None = None):
        self.client = SimpleNamespace(host=host)
        self.headers = headers or {}


def test_safe_redirect_path_allows_local_absolute_paths():
    assert safe_redirect_path("/packages?status=registered") == "/packages?status=registered"


def test_safe_redirect_path_blocks_external_urls():
    assert safe_redirect_path("https://evil.example/phish") == "/dashboard"
    assert safe_redirect_path("//evil.example/phish") == "/dashboard"
    assert safe_redirect_path("dashboard") == "/dashboard"
    assert safe_redirect_path("/\\evil") == "/dashboard"


def test_get_client_ip_trusts_forwarded_for_from_configured_proxy():
    request = _Request(
        "127.0.0.1",
        {"X-Forwarded-For": "198.51.100.25, 127.0.0.1"},
    )

    assert get_client_ip(request) == "198.51.100.25"


def test_get_client_ip_ignores_forwarded_for_from_untrusted_client():
    request = _Request(
        "203.0.113.10",
        {"X-Forwarded-For": "198.51.100.25"},
    )

    assert get_client_ip(request) == "203.0.113.10"
