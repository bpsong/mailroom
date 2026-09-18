"""Streak-3 regression + benchmark coverage (S11-S30).

Documents the S15 failure (2026-09-18, 20-case streak run):
  FAIL S15 "history reuse accepted".

Root causes (two, one harness + one genuine app hole):
  1. Harness artifact: the scenario created its user via raw SQL with NULL
     password_history, so the original hash was never recorded and reuse
     was (correctly per the code) accepted. Realistic flow is admin
     creation via user_service.create_user, which seeds history.
  2. Genuine hole: change_own_password/reset_user_password only consulted
     password_history and never compared against the CURRENT hash. Any row
     with NULL/empty history — notably the bootstrapped super_admin, whose
     INSERT omitted password_history — could "rotate" to the identical
     password, bypassing the rotation policy.

Fixes:
  - app/services/user_service.py: reject a new password that verifies
    against the current hash in both change_own_password and
    reset_user_password (same "recently used" message; no-op for
    well-formed rows where the current hash is already in history).
  - app/database/migrations.py: bootstrap_super_admin now seeds
    password_history with the initial hash.
"""

import asyncio
import json
import time
import uuid

from app.middleware.rate_limit import rate_limiter
from app.services.auth_service import auth_service
from app.database.connection import create_connection


def _reset():
    rate_limiter._requests.clear()


def test_password_reuse_blocked_via_realistic_flow(test_db, test_admin):
    """Admin-created user cannot rotate back to a recent password."""
    from app.models import UserCreate
    from app.services.user_service import user_service

    _reset()
    actor = asyncio.run(auth_service.authenticate_user(test_admin["username"], test_admin["password"]))
    uname = f"hist_{uuid.uuid4().hex[:6]}"
    created = asyncio.run(
        user_service.create_user(
            UserCreate(username=uname, password="StartPass12345!", full_name="H", role="operator"),
            actor,
        )
    )
    assert created.password_history is not None
    me = asyncio.run(auth_service.authenticate_user(uname, "StartPass12345!"))
    asyncio.run(user_service.change_own_password(me.id, "StartPass12345!", "SecondPass12345!"))
    me2 = asyncio.run(auth_service.authenticate_user(uname, "SecondPass12345!"))
    try:
        asyncio.run(user_service.change_own_password(me2.id, "SecondPass12345!", "StartPass12345!"))
        raise AssertionError("history reuse accepted")
    except ValueError as e:
        assert "recently" in str(e)


def test_same_as_current_rejected_with_null_history(test_db):
    """Legacy/NULL-history row cannot 'rotate' to the identical password."""
    from app.services.user_service import user_service

    _reset()
    uname = f"leg_{uuid.uuid4().hex[:6]}"
    ph = auth_service.hash_password("LegacyPass12345!")
    conn = create_connection(test_db)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [uname, ph, "L", "operator", True, False],
        )
    finally:
        conn.close()
    me = asyncio.run(auth_service.authenticate_user(uname, "LegacyPass12345!"))
    assert me.password_history is None
    try:
        asyncio.run(user_service.change_own_password(me.id, "LegacyPass12345!", "LegacyPass12345!"))
        raise AssertionError("same-as-current accepted")
    except ValueError as e:
        assert "recently" in str(e)


def test_admin_reset_to_same_password_rejected(test_db, test_admin, test_user):
    """Admin reset to the user's current password is rejected."""
    from app.services.user_service import user_service

    _reset()
    actor = asyncio.run(auth_service.authenticate_user(test_admin["username"], test_admin["password"]))
    target = asyncio.run(user_service.get_user_by_username(test_user["username"]))
    try:
        asyncio.run(
            user_service.reset_user_password(target.id, test_user["password"], force_change=False, actor=actor)
        )
        raise AssertionError("reset-to-same accepted")
    except ValueError as e:
        assert "recently" in str(e)


def test_bootstrap_seeds_password_history(tmp_path):
    """First super_admin starts with a seeded password history."""
    from app.database.migrations import MigrationManager
    from app.database.schema import init_database

    db_path = str(tmp_path / "boot.sqlite3")
    init_database(db_path)
    mgr = MigrationManager(db_path)
    result = mgr.bootstrap_super_admin(username="rootadmin", password="RootPass12345!")
    assert result.created
    conn = create_connection(db_path)
    try:
        row = conn.execute(
            "SELECT password_hash, password_history FROM users WHERE username=?", ["rootadmin"]
        ).fetchone()
    finally:
        conn.close()
    assert row[1], "bootstrap left password_history NULL"
    history = json.loads(row[1])
    assert len(history) == 1
    assert auth_service.verify_password("RootPass12345!", history[0])


def test_recipient_deactivate_blocks_package(test_db, test_user):
    """Deactivated recipients cannot receive new packages."""
    from app.models import PackageCreate, RecipientCreate
    from app.services.package_service import package_service
    from app.services.recipient_service import recipient_service

    _reset()
    t = uuid.uuid4().hex[:6]
    rec = asyncio.run(
        recipient_service.create_recipient(
            RecipientCreate(employee_id=f"Z{t}", name="Zed", email=f"z{t}@example.com", department="Ops")
        )
    )
    asyncio.run(recipient_service.deactivate_recipient(rec.id))
    actor = asyncio.run(auth_service.authenticate_user(test_user["username"], test_user["password"]))
    try:
        asyncio.run(
            package_service.create_package(
                PackageCreate(tracking_no=f"Z{t}", carrier="DHL", recipient_id=rec.id, notes=None), actor
            )
        )
        raise AssertionError("package for inactive recipient accepted")
    except ValueError as e:
        assert "not active" in str(e)


def test_streak3_perf_benchmarks(test_db, test_user, test_recipient):
    """Benchmark guards: search/autocomplete/dashboard <200ms, export <1s."""
    from app.models import PackageCreate, PackageFilters, Pagination
    from app.services.dashboard_service import dashboard_service
    from app.services.export_service import export_service
    from app.services.package_service import package_service
    from app.services.recipient_service import recipient_service

    _reset()
    actor = asyncio.run(auth_service.authenticate_user(test_user["username"], test_user["password"]))
    tag = uuid.uuid4().hex[:6].upper()
    for i in range(20):
        asyncio.run(
            package_service.create_package(
                PackageCreate(tracking_no=f"BMK{tag}{i:02d}", carrier="UPS",
                              recipient_id=test_recipient["id"], notes=None),
                actor,
            )
        )

    t0 = time.perf_counter()
    _, total = asyncio.run(
        package_service.search_packages(PackageFilters(query=tag), Pagination(limit=25, offset=0))
    )
    assert total == 20 and (time.perf_counter() - t0) * 1000 < 200

    t1 = time.perf_counter()
    asyncio.run(recipient_service.search_recipients(query="ZZZNOMATCH", limit=10))
    assert (time.perf_counter() - t1) * 1000 < 200

    t2 = time.perf_counter()
    stats = asyncio.run(dashboard_service.get_summary_stats())
    assert stats.total_packages >= 20 and (time.perf_counter() - t2) * 1000 < 200

    t3 = time.perf_counter()
    csv_text = asyncio.run(export_service.export_packages_csv())
    assert "Tracking Number" in csv_text and (time.perf_counter() - t3) * 1000 < 1000
