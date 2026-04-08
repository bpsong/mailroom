"""End-to-end tests for operator workflow (real form + CSRF flow)."""

from uuid import uuid4
import pytest

from app.database.connection import create_connection
from app.services.auth_service import auth_service


def _login_operator(client, username: str, password: str) -> str:
    """Login operator and return CSRF token for subsequent form posts."""
    forwarded_for = f"198.51.100.{int(uuid4().hex[:2], 16) % 250 + 1}"
    headers = {"X-Forwarded-For": forwarded_for}

    client.get("/auth/login", headers=headers)
    csrf_token = client.cookies.get("csrf_token")
    assert csrf_token

    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": csrf_token,
        },
        headers={"accept": "application/json", **headers},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    return client.cookies.get("csrf_token") or csrf_token


def _png_bytes() -> bytes:
    """Return minimal PNG-like payload accepted by magic-byte validation."""
    return b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)


@pytest.fixture
def operator_session(test_db):
    """Create operator user and recipient for workflow tests."""
    username = f"e2e_operator_{uuid4().hex[:8]}"
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)
    employee_id = f"EMP{uuid4().hex[:8]}"

    conn = create_connection(test_db)
    try:
        user_result = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "E2E Operator", "operator", True, False],
        ).fetchone()
        recipient_result = conn.execute(
            """
            INSERT INTO recipients (employee_id, name, email, department)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [employee_id, "Test Recipient", f"{employee_id.lower()}@example.com", "Engineering"],
        ).fetchone()
        assert user_result is not None
        assert recipient_result is not None

        yield {
            "user_id": user_result[0],
            "username": username,
            "password": password,
            "recipient_id": recipient_result[0],
        }
    finally:
        conn.close()


class TestOperatorWorkflow:
    """Test complete operator workflow from login to package delivery."""

    def test_complete_operator_workflow(self, client, operator_session, test_db):
        """Validate login + package registration path end-to-end."""
        csrf_token = _login_operator(client, operator_session["username"], operator_session["password"])

        tracking_no = f"E2E-TEST-{uuid4().hex[:8]}"
        register_response = client.post(
            "/packages/new",
            data={
                "tracking_no": tracking_no,
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
                "notes": "E2E test package",
                "csrf_token": csrf_token,
            },
        )
        assert register_response.status_code == 200

        conn = create_connection(test_db)
        try:
            row = conn.execute(
                "SELECT id, status FROM packages WHERE tracking_no = ?",
                [tracking_no],
            ).fetchone()
            assert row is not None
            assert row[1] == "registered"
        finally:
            conn.close()

    def test_operator_search_own_packages(self, client, operator_session):
        csrf_token = _login_operator(client, operator_session["username"], operator_session["password"])

        tracking_numbers = [f"SEARCH-{i}-{uuid4().hex[:6]}" for i in range(3)]
        for tracking_no in tracking_numbers:
            response = client.post(
                "/packages/new",
                data={
                    "tracking_no": tracking_no,
                    "carrier": "FedEx",
                    "recipient_id": str(operator_session["recipient_id"]),
                    "csrf_token": csrf_token,
                },
            )
            assert response.status_code == 200

        search_response = client.get("/packages?query=SEARCH-")
        assert search_response.status_code == 200
        body = search_response.text
        for tracking_no in tracking_numbers:
            assert tracking_no in body

    def test_operator_filter_by_status(self, client, operator_session, test_db):
        csrf_token = _login_operator(client, operator_session["username"], operator_session["password"])

        awaiting_tracking = f"AWAITING-{uuid4().hex[:6]}"
        registered_tracking = f"REGISTERED-{uuid4().hex[:6]}"

        response1 = client.post(
            "/packages/new",
            data={
                "tracking_no": awaiting_tracking,
                "carrier": "DHL",
                "recipient_id": str(operator_session["recipient_id"]),
                "csrf_token": csrf_token,
            },
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/packages/new",
            data={
                "tracking_no": registered_tracking,
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
                "csrf_token": csrf_token,
            },
        )
        assert response2.status_code == 200

        conn = create_connection(test_db)
        try:
            package_row = conn.execute(
                "SELECT id FROM packages WHERE tracking_no = ?",
                [awaiting_tracking],
            ).fetchone()
            assert package_row is not None
            awaiting_package_id = str(package_row[0])
        finally:
            conn.close()

        update_response = client.post(
            f"/packages/{awaiting_package_id}/status",
            data={
                "status": "awaiting_pickup",
                "notes": "Ready for pickup",
                "csrf_token": csrf_token,
            },
        )
        assert update_response.status_code == 200

        filtered = client.get("/packages?status=awaiting_pickup")
        assert filtered.status_code == 200
        assert awaiting_tracking in filtered.text
        assert registered_tracking not in filtered.text


class TestOperatorPhotoUpload:
    """Test operator photo upload workflow."""

    def test_upload_photo_during_registration(self, client, operator_session, test_db):
        csrf_token = _login_operator(client, operator_session["username"], operator_session["password"])

        tracking_no = f"PHOTO-{uuid4().hex[:8]}"
        response = client.post(
            "/packages/new",
            data={
                "tracking_no": tracking_no,
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
                "csrf_token": csrf_token,
            },
            files={"photo": ("package.png", _png_bytes(), "image/png")},
        )
        assert response.status_code == 200

        conn = create_connection(test_db)
        try:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM attachments a
                JOIN packages p ON p.id = a.package_id
                WHERE p.tracking_no = ?
                """,
                [tracking_no],
            ).fetchone()
            assert row is not None
            assert row[0] == 1
        finally:
            conn.close()

    def test_add_photo_after_registration(self, client, operator_session, test_db):
        csrf_token = _login_operator(client, operator_session["username"], operator_session["password"])

        tracking_no = f"PHOTO-LATER-{uuid4().hex[:8]}"
        create_response = client.post(
            "/packages/new",
            data={
                "tracking_no": tracking_no,
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
                "csrf_token": csrf_token,
            },
        )
        assert create_response.status_code == 200

        conn = create_connection(test_db)
        try:
            package_id_row = conn.execute(
                "SELECT id FROM packages WHERE tracking_no = ?",
                [tracking_no],
            ).fetchone()
            assert package_id_row is not None
            package_id = package_id_row[0]
        finally:
            conn.close()

        response = client.post(
            f"/packages/{package_id}/photo",
            data={"csrf_token": csrf_token},
            files={"photo": ("additional.png", _png_bytes(), "image/png")},
        )
        assert response.status_code == 200

        conn = create_connection(test_db)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM attachments WHERE package_id = ?",
                [str(package_id)],
            ).fetchone()
            assert row is not None
            assert row[0] == 1
        finally:
            conn.close()

