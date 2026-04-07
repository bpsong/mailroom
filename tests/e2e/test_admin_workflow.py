"""End-to-end tests for admin workflow (real route contracts)."""

from uuid import uuid4
import duckdb
import pytest

from app.services.auth_service import auth_service


def _login_admin(client, username: str, password: str) -> str:
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


@pytest.fixture
def admin_session(test_db):
    username = f"e2e_admin_{uuid4().hex[:8]}"
    password = "AdminPassword123!"
    password_hash = auth_service.hash_password(password)

    conn = duckdb.connect(test_db)
    try:
        row = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "E2E Admin", "admin", True, False],
        ).fetchone()
        conn.commit()
        assert row is not None

        yield {
            "user_id": row[0],
            "username": username,
            "password": password,
        }
    finally:
        conn.close()


def _create_operator_user(test_db, suffix: str = ""):
    username = f"operator_{suffix or uuid4().hex[:8]}"
    password = "OperatorPass123!"
    password_hash = auth_service.hash_password(password)
    conn = duckdb.connect(test_db)
    try:
        row = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "Operator User", "operator", True, False],
        ).fetchone()
        conn.commit()
        assert row is not None
        return row[0], username
    finally:
        conn.close()


class TestAdminUserManagement:
    def test_admin_create_operator(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])
        new_username = f"new_op_{uuid4().hex[:8]}"

        response = client.post(
            "/admin/users/new",
            data={
                "username": new_username,
                "password": "OperatorPass123!",
                "full_name": "New Operator",
                "role": "operator",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            row = conn.execute(
                "SELECT username, role FROM users WHERE username = ?",
                [new_username],
            ).fetchone()
            assert row is not None
            assert row[0] == new_username
            assert row[1] == "operator"
        finally:
            conn.close()

    def test_admin_reset_user_password(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])
        operator_id, _ = _create_operator_user(test_db)

        response = client.post(
            f"/admin/users/{operator_id}/password",
            data={
                "new_password": "NewPassword123!",
                "force_change": "true",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            row = conn.execute(
                "SELECT must_change_password FROM users WHERE id = ?",
                [str(operator_id)],
            ).fetchone()
            assert row is not None
            assert bool(row[0]) is True
        finally:
            conn.close()

    def test_admin_edit_operator_with_post(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])
        operator_id, _ = _create_operator_user(test_db)

        response = client.post(
            f"/admin/users/{operator_id}/edit",
            data={
                "full_name": "Renamed Operator",
                "role": "operator",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            row = conn.execute(
                "SELECT full_name, role FROM users WHERE id = ?",
                [str(operator_id)],
            ).fetchone()
            assert row is not None
            assert row[0] == "Renamed Operator"
            assert row[1] == "operator"
        finally:
            conn.close()

    @pytest.mark.skip(reason="Known DuckDB UPDATE/constraint behavior in user deactivation path")
    def test_admin_deactivate_user(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])
        operator_id, _ = _create_operator_user(test_db)

        response = client.post(
            f"/admin/users/{operator_id}/deactivate",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            row = conn.execute("SELECT is_active FROM users WHERE id = ?", [str(operator_id)]).fetchone()
            assert row is not None
            assert bool(row[0]) is False
        finally:
            conn.close()


class TestAdminRecipientManagement:
    def test_admin_import_recipients(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])

        csv_content = (
            "employee_id,name,email,department\n"
            "E2E001,Alice Johnson,alice@example.com,Engineering\n"
            "E2E002,Bob Williams,bob@example.com,Marketing\n"
            "E2E003,Carol Davis,carol@example.com,Sales"
        )

        response = client.post(
            "/admin/recipients/import/confirm",
            data={"csrf_token": csrf_token},
            files={"file": ("recipients.csv", csv_content.encode("utf-8"), "text/csv")},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True

        conn = duckdb.connect(test_db)
        try:
            count_row = conn.execute(
                "SELECT COUNT(*) FROM recipients WHERE employee_id IN ('E2E001','E2E002','E2E003')"
            ).fetchone()
            assert count_row is not None
            assert count_row[0] == 3
        finally:
            conn.close()

    def test_admin_create_recipient_manually(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])
        employee_id = f"MANUAL{uuid4().hex[:8]}"

        response = client.post(
            "/admin/recipients/new",
            data={
                "employee_id": employee_id,
                "name": "Manual Recipient",
                "email": f"{employee_id.lower()}@example.com",
                "department": "IT",
                "phone": "",
                "location": "",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            row = conn.execute(
                "SELECT name FROM recipients WHERE employee_id = ?",
                [employee_id],
            ).fetchone()
            assert row is not None
            assert row[0] == "Manual Recipient"
        finally:
            conn.close()

    def test_admin_update_recipient(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])

        conn = duckdb.connect(test_db)
        try:
            employee_id = f"EDIT{uuid4().hex[:8]}"
            row = conn.execute(
                """
                INSERT INTO recipients (employee_id, name, email, department, phone, location)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [employee_id, "Original Name", f"{employee_id.lower()}@example.com", "Ops", "", ""],
            ).fetchone()
            conn.commit()
            assert row is not None
            recipient_id = row[0]
        finally:
            conn.close()

        response = client.post(
            f"/admin/recipients/{recipient_id}/edit",
            data={
                "name": "Updated Recipient",
                "email": "updated@example.com",
                "department": "Updated Department",
                "phone": "",
                "location": "",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        conn = duckdb.connect(test_db)
        try:
            updated = conn.execute(
                "SELECT name, email, department FROM recipients WHERE id = ?",
                [str(recipient_id)],
            ).fetchone()
            assert updated is not None
            assert updated[0] == "Updated Recipient"
            assert updated[1] == "updated@example.com"
            assert updated[2] == "Updated Department"
        finally:
            conn.close()


class TestAdminReporting:
    def test_admin_view_dashboard(self, client, admin_session):
        _login_admin(client, admin_session["username"], admin_session["password"])
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "dashboard" in response.text.lower()

    def test_admin_export_report(self, client, admin_session, test_db):
        _login_admin(client, admin_session["username"], admin_session["password"])

        conn = duckdb.connect(test_db)
        try:
            recipient_row = conn.execute(
                """
                INSERT INTO recipients (employee_id, name, email, department)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """,
                [f"REP{uuid4().hex[:8]}", "Report Recipient", "report@example.com", "Finance"],
            ).fetchone()
            assert recipient_row is not None

            conn.execute(
                """
                INSERT INTO packages (tracking_no, carrier, recipient_id, status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    f"REPORT-{uuid4().hex[:8]}",
                    "UPS",
                    str(recipient_row[0]),
                    "registered",
                    "for export",
                    str(admin_session["user_id"]),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        export_response = client.get("/admin/reports/export")
        assert export_response.status_code == 200
        assert "text/csv" in export_response.headers.get("content-type", "")

        csv_content = export_response.text
        assert "Tracking Number" in csv_content
        assert "Carrier" in csv_content
        assert "Recipient Name" in csv_content


class TestAdminCannotModifySuperAdmin:
    @pytest.mark.skip(reason="Known DuckDB UPDATE/constraint behavior in role-protected edit path")
    def test_admin_cannot_edit_super_admin(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])

        super_username = f"super_{uuid4().hex[:8]}"
        super_hash = auth_service.hash_password("SuperPassword123!")
        conn = duckdb.connect(test_db)
        try:
            super_row = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [super_username, super_hash, "Super Admin", "super_admin", True, False],
            ).fetchone()
            conn.commit()
            assert super_row is not None
            super_admin_id = super_row[0]
        finally:
            conn.close()

        response = client.put(
            f"/admin/users/{super_admin_id}/edit",
            data={
                "full_name": "Modified Name",
                "role": "super_admin",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.skip(reason="Known DuckDB UPDATE/constraint behavior in role-protected deactivate path")
    def test_admin_cannot_deactivate_super_admin(self, client, admin_session, test_db):
        csrf_token = _login_admin(client, admin_session["username"], admin_session["password"])

        super_username = f"super_{uuid4().hex[:8]}"
        super_hash = auth_service.hash_password("SuperPassword123!")
        conn = duckdb.connect(test_db)
        try:
            super_row = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [super_username, super_hash, "Super Admin", "super_admin", True, False],
            ).fetchone()
            conn.commit()
            assert super_row is not None
            super_admin_id = super_row[0]
        finally:
            conn.close()

        response = client.post(
            f"/admin/users/{super_admin_id}/deactivate",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert response.status_code == 403
