"""End-to-end tests for operator workflow."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.services.auth_service import auth_service


pytestmark = pytest.mark.anyio


@pytest.fixture
async def operator_session():
    """Create operator user and session for E2E tests."""
    from app.database.write_queue import get_write_queue
    
    # Create operator user
    username = f"e2e_operator_{uuid4().hex[:8]}"
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)
    
    query = """
        INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
    """
    
    write_queue = await get_write_queue()
    result = await write_queue.execute(
        query,
        [username, password_hash, "E2E Operator", "operator", True, False],
        return_result=True,
    )
    
    user_id = result[0][0]
    
    # Create recipient for testing
    recipient_query = """
        INSERT INTO recipients (employee_id, name, email, department)
        VALUES (?, ?, ?, ?)
        RETURNING id
    """
    
    recipient_result = await write_queue.execute(
        recipient_query,
        [f"EMP{uuid4().hex[:8]}", "Test Recipient", "test@example.com", "Engineering"],
        return_result=True,
    )
    
    recipient_id = recipient_result[0][0]
    
    yield {
        "user_id": user_id,
        "username": username,
        "password": password,
        "recipient_id": recipient_id,
    }
    
    # Cleanup
    await write_queue.execute("DELETE FROM packages WHERE created_by = ?", [str(user_id)])
    await write_queue.execute("DELETE FROM recipients WHERE id = ?", [str(recipient_id)])
    await write_queue.execute("DELETE FROM users WHERE id = ?", [str(user_id)])


class TestOperatorWorkflow:
    """Test complete operator workflow from login to package delivery."""
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_complete_operator_workflow(self, operator_session):
        """
        Test complete operator workflow:
        1. Login
        2. Register package
        3. Update status to awaiting_pickup
        4. Update status to delivered
        """
        client = TestClient(app)
        
        # Step 1: Login
        from app.middleware.csrf import generate_csrf_token
        csrf_token = generate_csrf_token()
        client.cookies.set("csrf_token", csrf_token)
        
        login_response = client.post(
            "/auth/login",
            data={
                "username": operator_session["username"],
                "password": operator_session["password"],
                "csrf_token": csrf_token,
            },
        )
        
        assert login_response.status_code == 200
        assert "session_token" in client.cookies
        
        # Step 2: Register package
        register_response = client.post(
            "/packages/new",
            data={
                "tracking_no": "E2E-TEST-001",
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
                "notes": "E2E test package",
            },
        )
        
        assert register_response.status_code == 200
        package_data = register_response.json()
        package_id = package_data["id"]
        assert package_data["status"] == "registered"
        
        # Step 3: Update to awaiting_pickup
        update1_response = client.post(
            f"/packages/{package_id}/status",
            json={
                "status": "awaiting_pickup",
                "notes": "Package ready for pickup",
            },
        )
        
        assert update1_response.status_code == 200
        assert update1_response.json()["status"] == "awaiting_pickup"
        
        # Step 4: Update to delivered
        update2_response = client.post(
            f"/packages/{package_id}/status",
            json={
                "status": "delivered",
                "notes": "Package delivered to recipient",
            },
        )
        
        assert update2_response.status_code == 200
        assert update2_response.json()["status"] == "delivered"
        
        # Verify package timeline
        detail_response = client.get(f"/packages/{package_id}")
        assert detail_response.status_code == 200
        
        timeline = detail_response.json()["timeline"]
        assert len(timeline) == 3  # registered, awaiting_pickup, delivered
        assert timeline[0]["new_status"] == "registered"
        assert timeline[1]["new_status"] == "awaiting_pickup"
        assert timeline[2]["new_status"] == "delivered"
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_operator_search_own_packages(self, operator_session):
        """Test operator can search and view their own registered packages."""
        client = TestClient(app)
        
        # Login
        # ... login logic ...
        
        # Register multiple packages
        tracking_numbers = ["SEARCH-001", "SEARCH-002", "SEARCH-003"]
        
        for tracking_no in tracking_numbers:
            client.post(
                "/packages/new",
                data={
                    "tracking_no": tracking_no,
                    "carrier": "FedEx",
                    "recipient_id": str(operator_session["recipient_id"]),
                },
            )
        
        # Search for packages
        search_response = client.get("/packages?query=SEARCH")
        
        assert search_response.status_code == 200
        data = search_response.json()
        assert data["total"] >= 3
        
        # Verify all packages are in results
        found_tracking_nos = [pkg["tracking_no"] for pkg in data["packages"]]
        for tracking_no in tracking_numbers:
            assert tracking_no in found_tracking_nos
    
    @pytest.mark.skip(reason="Requires full database setup and authentication flow")
    async def test_operator_filter_by_status(self, operator_session):
        """Test operator can filter packages by status."""
        client = TestClient(app)
        
        # Login and register packages with different statuses
        # ... setup logic ...
        
        # Filter by awaiting_pickup
        response = client.get("/packages?status=awaiting_pickup")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned packages should have awaiting_pickup status
        for package in data["packages"]:
            assert package["status"] == "awaiting_pickup"


class TestOperatorPhotoUpload:
    """Test operator photo upload workflow."""
    
    @pytest.mark.skip(reason="Requires full database setup and file handling")
    async def test_upload_photo_during_registration(self, operator_session):
        """Test uploading photo during package registration."""
        client = TestClient(app)
        
        # Login
        # ... login logic ...
        
        # Create fake image file
        import io
        fake_image = io.BytesIO(b"fake image content")
        
        # Register package with photo
        response = client.post(
            "/packages/new",
            data={
                "tracking_no": "PHOTO-001",
                "carrier": "UPS",
                "recipient_id": str(operator_session["recipient_id"]),
            },
            files={"photo": ("package.jpg", fake_image, "image/jpeg")},
        )
        
        assert response.status_code == 200
        package_data = response.json()
        
        # Verify photo was attached
        package_id = package_data["id"]
        detail_response = client.get(f"/packages/{package_id}")
        assert len(detail_response.json()["attachments"]) == 1
    
    @pytest.mark.skip(reason="Requires full database setup and file handling")
    async def test_add_photo_after_registration(self, operator_session):
        """Test adding photo after package registration."""
        client = TestClient(app)
        
        # Login and register package
        # ... setup logic ...
        
        package_id = "..."
        
        # Add photo later
        import io
        fake_image = io.BytesIO(b"fake image content")
        
        response = client.post(
            f"/packages/{package_id}/photo",
            files={"photo": ("additional.jpg", fake_image, "image/jpeg")},
        )
        
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
