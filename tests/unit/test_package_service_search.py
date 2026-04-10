"""Tests for package search date filtering behavior."""

from datetime import datetime

import pytest

from app.database.connection import create_connection
from app.models import PackageFilters, Pagination
from app.services.package_service import PackageService


@pytest.mark.asyncio
async def test_search_packages_can_filter_using_updated_at(test_db):
    conn = create_connection(test_db)
    try:
        user_id = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            ["search_user", "hash", "Search User", "admin", True, False],
        ).fetchone()[0]
        recipient_id = conn.execute(
            """
            INSERT INTO recipients (employee_id, name, email, department)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            ["EMP-SEARCH", "Search Recipient", "search@example.com", "Ops"],
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO packages (
                id, tracking_no, carrier, recipient_id, status, notes,
                created_by, created_at, updated_at
            )
            VALUES (
                '00000000-0000-0000-0000-000000000001', ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                "3343244",
                "DHL",
                recipient_id,
                "delivered",
                "delivered later",
                user_id,
                datetime.fromisoformat("2026-04-08T13:44:56.806671"),
                datetime.fromisoformat("2026-04-10T06:39:16"),
            ],
        )
    finally:
        conn.close()

    service = PackageService()
    packages, total_count = await service.search_packages(
        PackageFilters(
            status="delivered",
            date_from=datetime.fromisoformat("2026-04-10T00:00:00"),
            date_field="updated_at",
        ),
        Pagination(limit=25, offset=0),
    )

    assert total_count == 1
    assert len(packages) == 1
    assert packages[0].tracking_no == "3343244"


@pytest.mark.asyncio
async def test_search_packages_still_defaults_date_filter_to_created_at(test_db):
    conn = create_connection(test_db)
    try:
        user_id = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            ["created_user", "hash", "Created User", "admin", True, False],
        ).fetchone()[0]
        recipient_id = conn.execute(
            """
            INSERT INTO recipients (employee_id, name, email, department)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            ["EMP-CREATED", "Created Recipient", "created@example.com", "Ops"],
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO packages (
                id, tracking_no, carrier, recipient_id, status, notes,
                created_by, created_at, updated_at
            )
            VALUES (
                '00000000-0000-0000-0000-000000000002', ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                "3343245",
                "DHL",
                recipient_id,
                "delivered",
                "created earlier",
                user_id,
                datetime.fromisoformat("2026-04-08T13:44:56.806671"),
                datetime.fromisoformat("2026-04-10T06:39:16"),
            ],
        )
    finally:
        conn.close()

    service = PackageService()
    packages, total_count = await service.search_packages(
        PackageFilters(
            status="delivered",
            date_from=datetime.fromisoformat("2026-04-10T00:00:00"),
        ),
        Pagination(limit=25, offset=0),
    )

    assert total_count == 0
    assert packages == []
