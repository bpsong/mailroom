"""Property-based tests for PackageService date range filter.

Feature: ui-improvements
Properties tested: 5
"""

import asyncio
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch

from app.database.connection import DatabaseConnection
from app.database.schema import SCHEMA_SQL
from app.database.write_queue import WriteQueue
from app.models.package import PackageFilters, Pagination
from app.services.package_service import PackageService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_temp_db() -> tuple[str, DatabaseConnection]:
    """Create a fresh temporary SQLite file with the full schema applied."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    db_path = tmp.name

    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.executescript(SCHEMA_SQL)
    conn.close()

    db_conn = DatabaseConnection(db_path)
    return db_path, db_conn


async def _make_service() -> tuple[PackageService, WriteQueue, DatabaseConnection, str]:
    """Return a PackageService wired to a fresh isolated database."""
    db_path, db_conn = _make_temp_db()
    wq = WriteQueue(db_path)
    await wq.start()
    service = PackageService()
    return service, wq, db_conn, db_path


async def _teardown(wq: WriteQueue, db_conn: DatabaseConnection, db_path: str) -> None:
    """Stop the write queue and clean up the temp database file."""
    await wq.stop()
    db_conn.close()
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db_path + suffix)
        except FileNotFoundError:
            pass


def _run(coro):
    """Run a coroutine in a fresh event loop (Hypothesis calls sync functions)."""
    return asyncio.run(coro)


def _seed_test_data(db_path: str, packages: list[dict]) -> tuple[str, str]:
    """
    Insert a user, recipient, and packages into the DB.
    Returns (user_id, recipient_id).
    """
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        user_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [user_id, f"user_{user_id[:8]}", "hash", "Test User", "operator", True, False],
        )

        recipient_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO recipients (id, employee_id, name, email, department, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [recipient_id, f"EMP{recipient_id[:8]}", "Test Recipient", "test@example.com", "Eng", True],
        )

        for pkg in packages:
            pkg_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO packages (id, tracking_no, carrier, recipient_id, status, notes,
                                      created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    pkg_id,
                    pkg["tracking_no"],
                    "UPS",
                    recipient_id,
                    "registered",
                    None,
                    user_id,
                    pkg["created_at"],
                    pkg["created_at"],
                ],
            )
    finally:
        conn.close()

    return user_id, recipient_id


# ---------------------------------------------------------------------------
# Property 5: Date range filter returns only in-range packages
# Validates: Requirements 7.2, 7.4
# ---------------------------------------------------------------------------

@given(
    # Number of days offset from a base date for each of 3 packages: before, inside, after
    days_before=st.integers(min_value=1, max_value=30),
    days_after=st.integers(min_value=1, max_value=30),
    range_days=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_property_5_date_range_filter_returns_only_in_range_packages(
    days_before, days_after, range_days
):
    """**Validates: Requirements 7.2, 7.4**

    For any date range [date_from, date_to], search_packages SHALL return only
    packages whose created_at falls within the inclusive range. Packages with
    dates strictly before date_from or strictly after date_to SHALL be excluded.
    """

    async def _run_test():
        service, wq, db_conn, db_path = await _make_service()
        try:
            with patch("app.services.package_service.get_db", return_value=db_conn):
                # Define a base date and range
                base = datetime(2024, 6, 15, 12, 0, 0)
                date_from = base
                date_to = base + timedelta(days=range_days)

                # Package before the range
                pkg_before_date = base - timedelta(days=days_before)
                # Package at the start of the range (inclusive)
                pkg_start_date = base
                # Package at the end of the range (inclusive)
                pkg_end_date = date_to
                # Package after the range
                pkg_after_date = date_to + timedelta(days=days_after)

                packages = [
                    {"tracking_no": "BEFORE001", "created_at": pkg_before_date},
                    {"tracking_no": "START001", "created_at": pkg_start_date},
                    {"tracking_no": "END001", "created_at": pkg_end_date},
                    {"tracking_no": "AFTER001", "created_at": pkg_after_date},
                ]
                _seed_test_data(db_path, packages)

                pagination = Pagination(limit=100, offset=0)

                # --- Test date_to only (Requirement 7.2) ---
                filters_to_only = PackageFilters(date_to=date_to)
                results_to_only, count_to_only = await service.search_packages(
                    filters_to_only, pagination
                )
                result_tracking_nos = {p.tracking_no for p in results_to_only}
                # Packages on or before date_to should be included
                assert "BEFORE001" in result_tracking_nos, (
                    "Package before date_to should be included when only date_to is set"
                )
                assert "START001" in result_tracking_nos, (
                    "Package at date_from (= date_to boundary) should be included"
                )
                assert "END001" in result_tracking_nos, (
                    "Package at date_to should be included (inclusive)"
                )
                # Package after date_to must be excluded
                assert "AFTER001" not in result_tracking_nos, (
                    "Package after date_to should be excluded"
                )

                # --- Test full range [date_from, date_to] (Requirement 7.4) ---
                filters_range = PackageFilters(date_from=date_from, date_to=date_to)
                results_range, count_range = await service.search_packages(
                    filters_range, pagination
                )
                range_tracking_nos = {p.tracking_no for p in results_range}

                # Packages within the inclusive range must be present
                assert "START001" in range_tracking_nos, (
                    "Package at date_from boundary should be included (inclusive)"
                )
                assert "END001" in range_tracking_nos, (
                    "Package at date_to boundary should be included (inclusive)"
                )
                # Packages outside the range must be excluded
                assert "BEFORE001" not in range_tracking_nos, (
                    "Package before date_from should be excluded from range filter"
                )
                assert "AFTER001" not in range_tracking_nos, (
                    "Package after date_to should be excluded from range filter"
                )

        finally:
            await _teardown(wq, db_conn, db_path)

    _run(_run_test())
