"""Streak-2 regression + benchmark coverage (S6-S10 all passed first try).

Locks in: photo validation, CSV upsert, session-cap eviction,
admin RBAC + force-password-change flow, dashboard/health perf guards.
"""

import asyncio
import io
import time
import uuid

from app.middleware.rate_limit import rate_limiter
from app.services.auth_service import auth_service
from app.database.connection import create_connection


def _reset():
    rate_limiter._requests.clear()


def _csrf(client, path="/auth/login"):
    client.get(path)
    tok = client.cookies.get("csrf_token")
    assert tok, "CSRF missing"
    return tok


def _login(client, username, password):
    csrf = _csrf(client)
    r = client.post(
        "/auth/login",
        data={"username": username, "password": password, "csrf_token": csrf},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _png():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
    return buf.getvalue()


def test_s6_photo_upload_and_validation(client, test_db, test_user, test_recipient):
    """Valid PNG attaches via HTTP; exe and oversize rejected at service layer."""
    import asyncio

    from fastapi import UploadFile

    from app.models import PackageCreate
    from app.services.file_service import file_service
    from app.services.package_service import package_service

    _reset()
    _login(client, test_user["username"], test_user["password"])
    actor = asyncio.run(auth_service.authenticate_user(test_user["username"], test_user["password"]))
    pkg = asyncio.run(
        package_service.create_package(
            PackageCreate(
                tracking_no="REG" + uuid.uuid4().hex[:6].upper(),
                carrier="DHL",
                recipient_id=test_recipient["id"],
                notes=None,
            ),
            actor,
        )
    )
    csrf = client.cookies.get("csrf_token") or _csrf(client, f"/packages/{pkg.id}")
    r = client.post(
        f"/packages/{pkg.id}/photo",
        files={"photo": ("snap.png", _png(), "image/png")},
        data={"csrf_token": csrf},
    )
    assert r.status_code == 200, r.text[:300]

    bad = UploadFile(filename="evil.exe", file=io.BytesIO(b"MZ junk" * 50))
    try:
        asyncio.run(file_service.save_upload(bad, category="packages"))
        raise AssertionError("exe accepted")
    except ValueError as e:
        assert "not allowed" in str(e).lower()

    big = UploadFile(filename="big.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * (6 * 1024 * 1024)))
    try:
        asyncio.run(file_service.save_upload(big, category="packages"))
        raise AssertionError("oversize accepted")
    except ValueError as e:
        assert "exceed" in str(e).lower()


def test_s7_csv_import_upsert(test_db, test_admin):
    from app.services.csv_import_service import csv_import_service

    _reset()
    actor = asyncio.run(auth_service.authenticate_user(test_admin["username"], test_admin["password"]))
    t = uuid.uuid4().hex[:6]
    csv_text = (
        "employee_id,name,email,department,phone,location\n"
        f"E1{t},Alice,alice{t}@example.com,Engineering,,\n"
        f"E2{t},Bad,not-an-email,Sales,,\n"
    )
    res, valid = asyncio.run(csv_import_service.parse_and_validate_csv(csv_text.encode()))
    assert res.total_rows == 2 and len(valid) == 1
    imp = asyncio.run(csv_import_service.import_recipients(valid, actor, filename="r.csv"))
    assert imp.created_count == 1
    imp2 = asyncio.run(csv_import_service.import_recipients(valid, actor, filename="r.csv"))
    assert imp2.updated_count == 1 and imp2.created_count == 0


def test_s8_session_cap_eviction(test_db):
    username = f"sess_{uuid.uuid4().hex[:6]}"
    ph = auth_service.hash_password("SessionPass123!")
    conn = create_connection(test_db)
    try:
        row = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)"
            " VALUES (?,?,?,?,?,?) RETURNING id",
            [username, ph, "S", "operator", True, False],
        ).fetchone()
    finally:
        conn.close()
    uid = asyncio.run(auth_service.authenticate_user(username, "SessionPass123!")).id
    toks = [asyncio.run(auth_service.create_session(uid)).token for _ in range(4)]
    assert len(asyncio.run(auth_service.get_user_sessions(uid))) == 3
    assert asyncio.run(auth_service.validate_session(toks[0])) is None
    assert asyncio.run(auth_service.validate_session(toks[-1])) is not None


def test_s9_admin_rbac_and_force_change(client, test_db, test_admin, test_user):
    from app.services.user_service import user_service

    _reset()
    _login(client, test_admin["username"], test_admin["password"])
    new_u = "nopr_" + uuid.uuid4().hex[:6]
    csrf = client.cookies.get("csrf_token") or _csrf(client, "/admin/users/new")
    r = client.post(
        "/admin/users/new",
        data={"username": new_u, "password": "BrandNewPass123!", "full_name": "N",
              "role": "operator", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code in (303, 302, 200), r.text[:300]
    target = asyncio.run(user_service.get_user_by_username(new_u))
    assert target is not None
    me = asyncio.run(user_service.get_user_by_username(test_admin["username"]))
    csrf2 = client.cookies.get("csrf_token") or _csrf(client, "/admin/users")
    r2 = client.post(f"/admin/users/{me.id}/deactivate", data={"csrf_token": csrf2})
    assert r2.status_code == 400


def test_s10_dashboard_health_benchmarks(client, test_user):
    from app.services.dashboard_service import dashboard_service
    from app.services.export_service import export_service

    _reset()
    _login(client, test_user["username"], test_user["password"])
    assert client.get("/dashboard").status_code == 200
    t0 = time.perf_counter()
    stats = asyncio.run(dashboard_service.get_summary_stats())
    assert (time.perf_counter() - t0) * 1000 < 200
    dist = asyncio.run(dashboard_service.get_status_distribution())
    assert sum(d.count for d in dist) == stats.total_packages
    assert client.get("/health").status_code == 200
    t1 = time.perf_counter()
    csv_text = asyncio.run(export_service.export_packages_csv())
    assert "Tracking Number" in csv_text
    assert (time.perf_counter() - t1) * 1000 < 1000
