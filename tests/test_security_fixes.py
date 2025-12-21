"""Tests for security fixes."""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.services.auth_service import auth_service
from app.models.recipient import RecipientCreate
from app.middleware.csrf import validate_csrf_token, generate_csrf_token
from fastapi import Request

# Configure pytest to use anyio for async tests
pytestmark = pytest.mark.anyio


class TestCSRFProtection:
    """Test CSRF protection fixes."""
    
    def test_csrf_token_generation(self):
        """Test CSRF token generation."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        assert token1 != token2
        assert len(token1) > 32
        assert len(token2) > 32
    
    def test_csrf_validation_requires_token(self):
        """Test CSRF validation requires matching tokens."""
        # Create mock request
        class MockRequest:
            def __init__(self):
                self.cookies = {}
                self.state = type('obj', (object,), {})()
        
        request = MockRequest()
        
        # Should fail without cookie token
        assert validate_csrf_token(request, "some_token") is False
        
        # Should fail with mismatched tokens
        request.cookies["csrf_token"] = "cookie_token"
        assert validate_csrf_token(request, "different_token") is False
        
        # Should succeed with matching tokens
        token = "matching_token"
        request.cookies["csrf_token"] = token
        assert validate_csrf_token(request, token) is True


class TestSessionLimits:
    """Test session limit enforcement.
    
    Note: These tests require database access and are marked as integration tests.
    They should be run separately with proper database setup.
    """
    
    @pytest.mark.skip(reason="Requires database setup - run as integration test")
    async def test_session_limit_enforcement(self):
        """Test that session limit is enforced."""
        user_id = uuid4()
        
        # Create 3 sessions (at limit)
        session1 = await auth_service.create_session(
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Test Browser 1"
        )
        session2 = await auth_service.create_session(
            user_id=user_id,
            ip_address="192.168.1.2",
            user_agent="Test Browser 2"
        )
        session3 = await auth_service.create_session(
            user_id=user_id,
            ip_address="192.168.1.3",
            user_agent="Test Browser 3"
        )
        
        # Verify all 3 sessions are valid
        assert await auth_service.validate_session(session1.token) is not None
        assert await auth_service.validate_session(session2.token) is not None
        assert await auth_service.validate_session(session3.token) is not None
        
        # Create 4th session (should evict oldest)
        session4 = await auth_service.create_session(
            user_id=user_id,
            ip_address="192.168.1.4",
            user_agent="Test Browser 4"
        )
        
        # Verify oldest session (session1) is terminated
        assert await auth_service.validate_session(session1.token) is None
        
        # Verify other sessions are still valid
        assert await auth_service.validate_session(session2.token) is not None
        assert await auth_service.validate_session(session3.token) is not None
        assert await auth_service.validate_session(session4.token) is not None
        
        # Cleanup
        await auth_service.terminate_user_sessions(user_id)
    
    @pytest.mark.skip(reason="Requires database setup - run as integration test")
    async def test_multiple_session_evictions(self):
        """Test that multiple old sessions are evicted if needed."""
        user_id = uuid4()
        
        # Create 5 sessions (2 over limit)
        sessions = []
        for i in range(5):
            session = await auth_service.create_session(
                user_id=user_id,
                ip_address=f"192.168.1.{i}",
                user_agent=f"Test Browser {i}"
            )
            sessions.append(session)
        
        # Only the last 3 should be valid
        assert await auth_service.validate_session(sessions[0].token) is None
        assert await auth_service.validate_session(sessions[1].token) is None
        assert await auth_service.validate_session(sessions[2].token) is not None
        assert await auth_service.validate_session(sessions[3].token) is not None
        assert await auth_service.validate_session(sessions[4].token) is not None
        
        # Cleanup
        await auth_service.terminate_user_sessions(user_id)
    
    def test_session_limit_configuration(self):
        """Test that session limit configuration is accessible."""
        from app.config import settings
        
        # Verify configuration exists
        assert hasattr(settings, 'max_concurrent_sessions')
        assert settings.max_concurrent_sessions == 3
        assert isinstance(settings.max_concurrent_sessions, int)


class TestDepartmentRequirement:
    """Test department field requirement."""
    
    def test_department_required_in_create(self):
        """Test that department is required when creating recipient."""
        # Should fail without department
        with pytest.raises(ValidationError) as exc_info:
            RecipientCreate(
                employee_id="EMP001",
                name="John Doe",
                email="john@example.com",
                # department missing
            )
        
        # Verify error is about department field
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('department',) for error in errors)
    
    def test_department_cannot_be_empty(self):
        """Test that department cannot be empty string."""
        # Should fail with empty department
        with pytest.raises(ValidationError) as exc_info:
            RecipientCreate(
                employee_id="EMP001",
                name="John Doe",
                email="john@example.com",
                department="",  # Empty string
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('department',) for error in errors)
    
    def test_department_valid_creation(self):
        """Test that recipient can be created with valid department."""
        # Should succeed with valid department
        recipient = RecipientCreate(
            employee_id="EMP001",
            name="John Doe",
            email="john@example.com",
            department="Engineering",
        )
        
        assert recipient.department == "Engineering"
        assert recipient.employee_id == "EMP001"
        assert recipient.name == "John Doe"
        assert recipient.email == "john@example.com"
    
    def test_department_with_whitespace(self):
        """Test that department with only whitespace is invalid."""
        # Should fail with whitespace-only department
        with pytest.raises(ValidationError) as exc_info:
            RecipientCreate(
                employee_id="EMP001",
                name="John Doe",
                email="john@example.com",
                department="   ",  # Only whitespace
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('department',) for error in errors)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
