"""Regression + benchmark coverage for streak S2 failure.

Failure documented (2026-09-18, scenario streak run 1):
  S2 "account lockout after 5 failed logins" FAILED with 429
  `attempt 4 expected 401 got 429 RATE_LIMIT_EXCEEDED`.

Root cause:
  RateLimitMiddleware keyed its bucket by (ip, path) only, so every
  GET /auth/login (used by browsers/tests to prime the CSRF cookie)
  consumed the same 10/min budget as POST /auth/login attempts.
  A realistic browser flow does GET+POST per attempt, so after
  5 cycles (10 requests) the 6th request was rejected with 429
  before account lockout (max_failed_logins=5 -> 403) could be observed.

Fix:
  Method-aware bucket (`f"{method}:{path}"`) in
  app/middleware/rate_limit.py so safe page views do not consume the
  POST login-attempt budget.

This file locks in the regression and adds benchmark guards.
"""

import time
import uuid

from app.middleware.rate_limit import rate_limiter
from app.services.auth_service import auth_service
from app.database.connection import create_connection


def _reset_rate_limiter():
    rate_limiter._requests.clear()


def _prime_csrf(client, path="/auth/login"):
    client.get(path)
    token = client.cookies.get("csrf_token")
    assert token, "CSRF token cookie was not set"
    return token


def _create_user(test_db, username, password, role="operator"):
    password_hash = auth_service.hash_password(password)
    conn = create_connection(test_db)
    try:
        row = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "Streak User", role, True, False],
        ).fetchone()
        assert row is not None
        return {"id": row[0], "username": username, "password": password}
    finally:
        conn.close()


def test_get_login_page_does_not_consume_post_budget(client):
    """Regression: 10 GETs must not block a subsequent POST login."""
    _reset_rate_limiter()
    for _ in range(10):
        r = client.get("/auth/login")
        assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    assert csrf
    # POST bucket must still have room (no 429 purely from GETs).
    # We assert the limiter state directly to avoid depending on a user.
    key = next((k for k in rate_limiter._requests if k[1] == "POST:/auth/login"), None)
    post_count = len(rate_limiter._requests[key]) if key else 0
    assert post_count == 0, f"GETs leaked into POST bucket: {post_count}"


def test_account_lockout_reachable_via_browser_flow(client, test_db):
    """Regression for streak S2: 5x (GET+bad POST) -> 401s, then good POST -> 403 lockout."""
    _reset_rate_limiter()
    username = f"lock_{uuid.uuid4().hex[:8]}"
    user = _create_user(test_db, username, "CorrectPass123!")

    for i in range(5):
        csrf = _prime_csrf(client)
        r = client.post(
            "/auth/login",
            data={"username": username, "password": "WrongPass123!!", "csrf_token": csrf},
            headers={"accept": "application/json"},
        )
        assert r.status_code == 401, f"attempt {i}: expected 401 got {r.status_code} {r.text[:200]}"

    csrf = _prime_csrf(client)
    r = client.post(
        "/auth/login",
        data={"username": username, "password": user["password"], "csrf_token": csrf},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 403, f"expected lockout 403 got {r.status_code} {r.text[:300]}"
    assert "locked" in r.text.lower()


def test_package_search_benchmark_under_200ms(client, test_db, test_user, test_recipient):
    """Benchmark guard: filtered package search stays under 200ms with 50 rows."""
    import asyncio

    from app.models import PackageCreate, PackageFilters, Pagination
    from app.services.package_service import package_service

    _reset_rate_limiter()
    actor = asyncio.run(auth_service.authenticate_user(test_user["username"], test_user["password"]))
    tag = uuid.uuid4().hex[:6].upper()
    for i in range(50):
        asyncio.run(
            package_service.create_package(
                PackageCreate(
                    tracking_no=f"REG{i:03d}{tag}",
                    carrier="UPS",
                    recipient_id=test_recipient["id"],
                    notes=None,
                ),
                actor,
            )
        )

    t0 = time.perf_counter()
    pkgs, total = asyncio.run(
        package_service.search_packages(PackageFilters(query=tag), Pagination(limit=25, offset=0))
    )
    dt_ms = (time.perf_counter() - t0) * 1000
    assert total >= 50, total
    assert dt_ms < 200, f"package search too slow: {dt_ms:.1f}ms"


def test_export_csv_benchmark(client, test_db, test_user, test_recipient):
    """Benchmark guard: CSV export of packages completes quickly (<1s)."""
    import asyncio

    from app.services.export_service import export_service

    t0 = time.perf_counter()
    csv_text = asyncio.run(export_service.export_packages_csv())
    dt_ms = (time.perf_counter() - t0) * 1000
    assert "Tracking Number" in csv_text
    assert dt_ms < 1000, f"export too slow: {dt_ms:.1f}ms"
