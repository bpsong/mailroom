"""End-to-end tests for concurrent-like operations (stable coverage)."""

from uuid import uuid4
import duckdb
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import auth_service


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
    conn = duckdb.connect(test_db)
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
        conn.commit()

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

        conn = duckdb.connect(multiple_operators["test_db"])
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

        conn = duckdb.connect(multiple_operators["test_db"])
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
    @pytest.mark.skip(reason="Requires dedicated multi-admin import orchestration and deterministic merge checks")
    def test_concurrent_csv_imports(self):
        pass


class TestDatabaseWriteQueue:
    @pytest.mark.skip(reason="Requires dedicated load profile/stress harness")
    def test_write_queue_handles_concurrent_writes(self):
        pass

    @pytest.mark.skip(reason="Requires dedicated load profile/stress harness")
    def test_no_database_locking_under_load(self):
        pass

