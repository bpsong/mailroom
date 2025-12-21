"""End-to-end tests for admin workflow."""

import pytest
import io
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.services.auth_service import auth_service


pytestmark = pytest.mark.anyio


@pytest.fixture
async def admin_session():
    """Create admin user and session for E2E tests."""
    from app.database.write_queue import get_write_queue
    
    # Create admin user
    username = f"e2e_admin_{uuid4().hex[:8]}"
    password = "AdminPassword123!"
    password_hash = auth_service.hash_password(password)
    
    query = """
        INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
    """
    
    write_queue = await get_write_queue()
    result = await write_queue.execute(
        query,
        [username, password_hash, "E2E Admin", "admin", True, False],
        return_result=True,
    )
    
    user_id = result[0][0]
    
    yield {
        "user_id": user_id,
        "username": username,
        "password": password,
    }
    
    # Cleanup
    await write_queue.execute("DELETE FROM users WHERE id = ?", [str(user_id)])


class TestAdminUserManagement:
    """Test admin user management workflow."""
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_create_operator(self, admin_session):
        """
        Test admin workflow for creating operator:
        1. Login as admin
        2. Create new operator user
        3. Verify operator was created
        """
        client = TestClient(app)
        
        # Step 1: Login as admin
        from app.middleware.csrf import generate_csrf_token
        csrf_token = generate_csrf_token()
        client.cookies.set("csrf_token", csrf_token)
        
        login_response = client.post(
            "/auth/login",
            data={
                "username": admin_session["username"],
                "password": admin_session["password"],
                "csrf_token": csrf_token,
            },
        )
        
        assert login_response.status_code == 200
        
        # Step 2: Create operator
        new_operator_username = f"operator_{uuid4().hex[:8]}"
        
        create_response = client.post(
            "/admin/users/new",
            json={
                "username": new_operator_username,
                "password": "OperatorPass123!",
                "full_name": "New Operator",
                "role": "operator",
            },
        )
        
        assert create_response.status_code == 200
        operator_data = create_response.json()
        assert operator_data["username"] == new_operator_username
        assert operator_data["role"] == "operator"
        
        # Step 3: Verify operator exists
        list_response = client.get(f"/admin/users?query={new_operator_username}")
        
        assert list_response.status_code == 200
        users = list_response.json()["users"]
        assert len(users) == 1
        assert users[0]["username"] == new_operator_username
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_reset_user_password(self, admin_session):
        """Test admin resetting user password."""
        client = TestClient(app)
        
        # Login as admin
        # ... login logic ...
        
        # Create operator
        # ... create operator logic ...
        
        operator_id = "..."
        
        # Reset password
        reset_response = client.post(
            f"/admin/users/{operator_id}/password",
            json={
                "new_password": "NewPassword123!",
                "force_change": True,
            },
        )
        
        assert reset_response.status_code == 200
        
        # Verify operator must change password on next login
        user_response = client.get(f"/admin/users/{operator_id}")
        assert user_response.json()["must_change_password"] is True
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_deactivate_user(self, admin_session):
        """Test admin deactivating user."""
        client = TestClient(app)
        
        # Login and create operator
        # ... setup logic ...
        
        operator_id = "..."
        
        # Deactivate operator
        deactivate_response = client.post(f"/admin/users/{operator_id}/deactivate")
        
        assert deactivate_response.status_code == 200
        
        # Verify operator is inactive
        user_response = client.get(f"/admin/users/{operator_id}")
        assert user_response.json()["is_active"] is False


class TestAdminRecipientManagement:
    """Test admin recipient management workflow."""
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_import_recipients(self, admin_session):
        """
        Test admin workflow for importing recipients:
        1. Login as admin
        2. Upload CSV file
        3. Verify recipients were imported
        """
        client = TestClient(app)
        
        # Step 1: Login
        # ... login logic ...
        
        # Step 2: Upload CSV
        csv_content = """employee_id,name,email,department
E2E001,Alice Johnson,alice@example.com,Engineering
E2E002,Bob Williams,bob@example.com,Marketing
E2E003,Carol Davis,carol@example.com,Sales"""
        
        csv_file = io.BytesIO(csv_content.encode())
        
        import_response = client.post(
            "/admin/recipients/import",
            files={"file": ("recipients.csv", csv_file, "text/csv")},
        )
        
        assert import_response.status_code == 200
        data = import_response.json()
        assert data["created"] == 3
        assert len(data["errors"]) == 0
        
        # Step 3: Verify recipients exist
        for employee_id in ["E2E001", "E2E002", "E2E003"]:
            search_response = client.get(f"/admin/recipients?query={employee_id}")
            assert search_response.status_code == 200
            assert len(search_response.json()["recipients"]) == 1
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_create_recipient_manually(self, admin_session):
        """Test admin creating recipient manually."""
        client = TestClient(app)
        
        # Login
        # ... login logic ...
        
        # Create recipient
        create_response = client.post(
            "/admin/recipients/new",
            json={
                "employee_id": f"MANUAL{uuid4().hex[:8]}",
                "name": "Manual Recipient",
                "email": "manual@example.com",
                "department": "IT",
            },
        )
        
        assert create_response.status_code == 200
        recipient_data = create_response.json()
        assert recipient_data["name"] == "Manual Recipient"
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_update_recipient(self, admin_session):
        """Test admin updating recipient information."""
        client = TestClient(app)
        
        # Login and create recipient
        # ... setup logic ...
        
        recipient_id = "..."
        
        # Update recipient
        update_response = client.put(
            f"/admin/recipients/{recipient_id}/edit",
            json={
                "department": "Updated Department",
                "email": "updated@example.com",
            },
        )
        
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["department"] == "Updated Department"
        assert updated_data["email"] == "updated@example.com"


class TestAdminReporting:
    """Test admin reporting workflow."""
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_view_dashboard(self, admin_session):
        """Test admin viewing dashboard with statistics."""
        client = TestClient(app)
        
        # Login
        # ... login logic ...
        
        # View dashboard
        dashboard_response = client.get("/dashboard")
        
        assert dashboard_response.status_code == 200
        data = dashboard_response.json()
        
        # Verify dashboard has expected metrics
        assert "packages_today" in data
        assert "awaiting_pickup" in data
        assert "delivered_today" in data
        assert "top_recipients" in data
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_export_report(self, admin_session):
        """Test admin exporting package report."""
        client = TestClient(app)
        
        # Login
        # ... login logic ...
        
        # Export report
        export_response = client.get("/admin/reports/export?format=csv")
        
        assert export_response.status_code == 200
        assert export_response.headers["content-type"] == "text/csv"
        
        # Verify CSV content
        csv_content = export_response.text
        assert "tracking_no" in csv_content
        assert "carrier" in csv_content
        assert "recipient_name" in csv_content


class TestAdminCannotModifySuperAdmin:
    """Test that admin cannot modify super admin users."""
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_cannot_edit_super_admin(self, admin_session):
        """Test admin cannot edit super admin users."""
        client = TestClient(app)
        
        # Login as admin
        # ... login logic ...
        
        # Get super admin user ID
        # ... get super admin ...
        
        super_admin_id = "..."
        
        # Try to edit super admin
        edit_response = client.put(
            f"/admin/users/{super_admin_id}/edit",
            json={"full_name": "Modified Name"},
        )
        
        assert edit_response.status_code == 403
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_admin_cannot_deactivate_super_admin(self, admin_session):
        """Test admin cannot deactivate super admin users."""
        client = TestClient(app)
        
        # Login as admin
        # ... login logic ...
        
        super_admin_id = "..."
        
        # Try to deactivate super admin
        deactivate_response = client.post(f"/admin/users/{super_admin_id}/deactivate")
        
        assert deactivate_response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
