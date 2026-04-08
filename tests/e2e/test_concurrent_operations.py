"""End-to-end tests for concurrent-like operations (stable coverage)."""

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.connection import create_connection
from app.main import app
from app.models import RecipientCreate
from app.services.auth_service import auth_service
from app.services.csv_import_service import csv_import_service
from app.services.recipient_service import recipient_service
from app.services.user_service import user_service


def _login(client: TestClient, username: str, password: str) -> str:
    forwarded_for = f"198.51.100.{int(uuid4().hex[:2], 16) % 250 + 1}"
    headers = {"X-Forwarded-For": forwarded_for}

    client.get("/auth/login", headers=headers)
    csrf_token = client.cookies.get("csrf_token")
    assert csrf_token
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password, "csrf_token": csrf_token},
        headers={"accept": "application/json", **headers},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    return client.cookies.get("csrf_token") or csrf_token


@pytest.fixture
def multiple_operators(test_db):
    conn = create_connection(test_db)
    try:
        operators = []
        for i in range(3):
            username = f"concurrent_op_{i}_{uuid4().hex[:8]}"
            password = "TestPassword123!"
            password_hash = auth_service.hash_password(password)
            row = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [username, password_hash, f"Operator {i}", "operator", True, False],
            ).fetchone()
            assert row is not None
            operators.append({"id": row[0], "username": username, "password": password})

        recipient_row = conn.execute(
            """
            INSERT INTO recipients (employee_id, name, email, department)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [f"SHARED{uuid4().hex[:8]}", "Shared Recipient", "shared@example.com", "Engineering"],
        ).fetchone()
        assert recipient_row is not None
        yield {"operators": operators, "recipient_id": recipient_row[0], "test_db": test_db}
    finally:
        conn.close()


class TestConcurrentPackageRegistration:
    def test_multiple_operators_register_packages_simultaneously(self, multiple_operators):
        """Feasible approximation: rapid multi-client registrations."""
        tracking_nos = [f"CONCURRENT-{i}-{uuid4().hex[:8]}" for i in range(3)]

        for op, tracking in zip(multiple_operators["operators"], tracking_nos):
            client = TestClient(app)
            csrf = _login(client, op["username"], op["password"])
            response = client.post(
                "/packages/new",
                data={
                    "tracking_no": tracking,
                    "carrier": "UPS",
                    "recipient_id": str(multiple_operators["recipient_id"]),
                    "csrf_token": csrf,
                },
            )
            assert response.status_code == 200

        conn = create_connection(multiple_operators["test_db"])
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM packages WHERE tracking_no LIKE 'CONCURRENT-%'"
            ).fetchone()
            assert row is not None
            assert row[0] == 3
        finally:
            conn.close()


class TestConcurrentSessionManagement:
    def test_multiple_concurrent_logins(self, multiple_operators):
        """Feasible approximation: repeated multi-client logins."""
        for operator in multiple_operators["operators"]:
            client = TestClient(app)
            csrf = _login(client, operator["username"], operator["password"])
            assert csrf
            assert client.cookies.get("session_token")

    def test_session_limit_enforcement_concurrent(self, multiple_operators):
        """Validate cap after rapid repeated logins for same user."""
        operator = multiple_operators["operators"][0]

        for _ in range(5):
            client = TestClient(app)
            _login(client, operator["username"], operator["password"])

        conn = create_connection(multiple_operators["test_db"])
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP",
                [str(operator["id"])],
            ).fetchone()
            assert row is not None
            assert row[0] <= 3
        finally:
            conn.close()


class TestConcurrentCSVImport:
    @pytest.mark.asyncio
    async def test_concurrent_csv_imports(self, test_admin, test_db):
        actor = await user_service.get_user_by_id(test_admin["id"])
        assert actor is not None

        batch_one = [
            RecipientCreate(
                employee_id=f"CSV-A-{i}-{uuid4().hex[:6]}",
                name=f"Batch A {i}",
                email=f"batch-a-{i}-{uuid4().hex[:6]}@example.com",
                department="Operations",
                phone=None,
                location=None,
            )
            for i in range(2)
        ]
        batch_two = [
            RecipientCreate(
                employee_id=f"CSV-B-{i}-{uuid4().hex[:6]}",
                name=f"Batch B {i}",
                email=f"batch-b-{i}-{uuid4().hex[:6]}@example.com",
                department="Engineering",
                phone=None,
                location=None,
            )
            for i in range(2)
        ]

        results = await asyncio.gather(
            csv_import_service.import_recipients(batch_one, actor, filename="batch-one.csv"),
            csv_import_service.import_recipients(batch_two, actor, filename="batch-two.csv"),
        )

        assert sum(result.created_count for result in results) == 4
        conn = create_connection(test_db)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM recipients WHERE employee_id LIKE 'CSV-%'"
            ).fetchone()
            assert row is not None
            assert row[0] == 4
        finally:
            conn.close()


class TestDatabaseWriteQueue:
    @pytest.mark.asyncio
    async def test_write_queue_handles_concurrent_writes(self, test_db):
        async def insert_auth_event(index: int) -> None:
            await auth_service.log_auth_event(
                event_type="load_test",
                username=f"queue-user-{index}",
                details=f'{{"index": {index}}}',
            )

        await asyncio.gather(*(insert_auth_event(i) for i in range(12)))

        conn = create_connection(test_db)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM auth_events WHERE event_type = 'load_test'"
            ).fetchone()
            assert row is not None
            assert row[0] == 12
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_no_database_locking_under_load(self, test_db):
        async def create_recipient(index: int) -> None:
            await recipient_service.create_recipient(
                RecipientCreate(
                    employee_id=f"LOAD-{index}-{uuid4().hex[:6]}",
                    name=f"Load Recipient {index}",
                    email=f"load-{index}-{uuid4().hex[:6]}@example.com",
                    department="Load Test",
                    phone=None,
                    location=None,
                )
            )

        await asyncio.gather(*(create_recipient(i) for i in range(10)))

        conn = create_connection(test_db)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM recipients WHERE employee_id LIKE 'LOAD-%'"
            ).fetchone()
            assert row is not None
            assert row[0] == 10
        finally:
            conn.close()

