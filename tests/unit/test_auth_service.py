"""Unit tests for AuthService."""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4
from types import SimpleNamespace

from app.services.auth_service import auth_service, AuthenticationError
from app.config import settings


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing produces different hashes."""
        password = "TestPassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        password_hash = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, password_hash) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        password_hash = auth_service.hash_password(password)
        
        assert auth_service.verify_password(wrong_password, password_hash) is False


class TestPasswordStrengthValidation:
    """Test password strength validation."""
    
    def test_password_too_short(self):
        """Test password shorter than minimum length."""
        password = "Short1!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert error_msg is not None
        assert "at least" in error_msg.lower()
        assert str(settings.password_min_length) in error_msg
    
    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        password = "testpassword123!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert error_msg is not None
        assert "uppercase" in error_msg.lower()
    
    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        password = "TESTPASSWORD123!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert error_msg is not None
        assert "lowercase" in error_msg.lower()
    
    def test_password_no_digit(self):
        """Test password without digit."""
        password = "TestPassword!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert error_msg is not None
        assert "digit" in error_msg.lower()
    
    def test_password_no_special_char(self):
        """Test password without special character."""
        password = "TestPassword123"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert error_msg is not None
        assert "special character" in error_msg.lower()
    
    def test_password_valid(self):
        """Test valid password meeting all requirements."""
        password = "ValidPassword123!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is True
        assert error_msg is None


class TestPasswordHistory:
    """Test password history checking."""
    
    def test_check_password_history_empty(self):
        """Test password history check with no history."""
        password = "TestPassword123!"
        
        assert auth_service.check_password_history(password, None) is False
        assert auth_service.check_password_history(password, "") is False
    
    def test_check_password_history_not_in_history(self):
        """Test password not in history."""
        old_password = "OldPassword123!"
        new_password = "NewPassword456!"
        
        old_hash = auth_service.hash_password(old_password)
        history = json.dumps([old_hash])
        
        assert auth_service.check_password_history(new_password, history) is False
    
    def test_check_password_history_in_history(self):
        """Test password found in history."""
        password = "TestPassword123!"
        
        password_hash = auth_service.hash_password(password)
        history = json.dumps([password_hash])
        
        assert auth_service.check_password_history(password, history) is True
    
    def test_check_password_history_multiple_entries(self):
        """Test password history with multiple entries."""
        password1 = "Password1!"
        password2 = "Password2!"
        password3 = "Password3!"
        
        hash1 = auth_service.hash_password(password1)
        hash2 = auth_service.hash_password(password2)
        hash3 = auth_service.hash_password(password3)
        
        history = json.dumps([hash1, hash2, hash3])
        
        # All three passwords should be found in history
        assert auth_service.check_password_history(password1, history) is True
        assert auth_service.check_password_history(password2, history) is True
        assert auth_service.check_password_history(password3, history) is True
        
        # New password should not be in history
        assert auth_service.check_password_history("NewPassword4!", history) is False
    
    def test_check_password_history_invalid_json(self):
        """Test password history with invalid JSON."""
        password = "TestPassword123!"
        invalid_history = "not valid json"
        
        # Should return False for invalid JSON
        assert auth_service.check_password_history(password, invalid_history) is False


class TestPasswordHistoryUpdate:
    """Test password history update."""
    
    def test_update_password_history_empty(self):
        """Test updating empty password history."""
        new_hash = "new_hash_value"
        
        updated_history = auth_service.update_password_history(new_hash, None)
        history_list = json.loads(updated_history)
        
        assert len(history_list) == 1
        assert history_list[0] == new_hash
    
    def test_update_password_history_existing(self):
        """Test updating existing password history."""
        old_hash = "old_hash_value"
        new_hash = "new_hash_value"
        
        existing_history = json.dumps([old_hash])
        updated_history = auth_service.update_password_history(new_hash, existing_history)
        history_list = json.loads(updated_history)
        
        assert len(history_list) == 2
        assert history_list[0] == old_hash
        assert history_list[1] == new_hash
    
    def test_update_password_history_limit(self):
        """Test password history respects limit."""
        # Create history with max entries
        hashes = [f"hash_{i}" for i in range(settings.password_history_count + 1)]
        existing_history = json.dumps(hashes)
        
        new_hash = "new_hash"
        updated_history = auth_service.update_password_history(new_hash, existing_history)
        history_list = json.loads(updated_history)
        
        # Should keep only last N+1 entries
        assert len(history_list) == settings.password_history_count + 1
        assert history_list[-1] == new_hash
        assert hashes[0] not in history_list  # Oldest should be removed


class TestSessionToken:
    """Test session token generation."""
    
    def test_generate_session_token(self):
        """Test session token generation."""
        token1 = auth_service.generate_session_token()
        token2 = auth_service.generate_session_token()
        
        # Tokens should be unique
        assert token1 != token2
        
        # Tokens should be reasonably long
        assert len(token1) > 32
        assert len(token2) > 32
        
        # Tokens should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token1)
        assert all(c.isalnum() or c in '-_' for c in token2)


class TestAuthenticateUser:
    """Test login authentication logic extracted into the service layer."""

    @staticmethod
    def _patch_db(monkeypatch, row):
        class FakeCursor:
            def fetchone(self):
                return row

        class FakeConnection:
            def execute(self, query, params):
                return FakeCursor()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_db = SimpleNamespace(get_read_connection=lambda: FakeConnection())
        monkeypatch.setattr("app.database.connection.get_db", lambda: fake_db)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, monkeypatch):
        password = "ValidPassword123!"
        password_hash = auth_service.hash_password(password)
        user_id = uuid4()
        now = datetime.now()
        row = (
            user_id,
            "testuser",
            password_hash,
            "Test User",
            "operator",
            True,
            False,
            None,
            2,
            None,
            now,
            now,
        )

        self._patch_db(monkeypatch, row)

        reset_calls = []

        async def fake_check_account_lockout(username):
            return False, None

        async def fake_reset_failed_login(username):
            reset_calls.append(username)

        monkeypatch.setattr(auth_service, "check_account_lockout", fake_check_account_lockout)
        monkeypatch.setattr(auth_service, "reset_failed_login", fake_reset_failed_login)

        user = await auth_service.authenticate_user(
            username="testuser",
            password=password,
            ip_address="127.0.0.1",
        )

        assert user.id == user_id
        assert user.username == "testuser"
        assert reset_calls == ["testuser"]

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, monkeypatch):
        password_hash = auth_service.hash_password("ValidPassword123!")
        now = datetime.now()
        row = (
            uuid4(),
            "testuser",
            password_hash,
            "Test User",
            "operator",
            True,
            False,
            None,
            0,
            None,
            now,
            now,
        )

        self._patch_db(monkeypatch, row)

        increment_calls = []
        log_calls = []

        async def fake_check_account_lockout(username):
            return False, None

        async def fake_increment_failed_login(username):
            increment_calls.append(username)

        async def fake_log_auth_event(**kwargs):
            log_calls.append(kwargs)

        monkeypatch.setattr(auth_service, "check_account_lockout", fake_check_account_lockout)
        monkeypatch.setattr(auth_service, "increment_failed_login", fake_increment_failed_login)
        monkeypatch.setattr(auth_service, "log_auth_event", fake_log_auth_event)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(
                username="testuser",
                password="WrongPassword456!",
                ip_address="127.0.0.1",
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.reason == "invalid_password"
        assert increment_calls == ["testuser"]
        assert log_calls[0]["details"] == json.dumps({"reason": "invalid_password"})

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_username(self, monkeypatch):
        self._patch_db(monkeypatch, None)

        log_calls = []

        async def fake_check_account_lockout(username):
            return False, None

        async def fake_log_auth_event(**kwargs):
            log_calls.append(kwargs)

        monkeypatch.setattr(auth_service, "check_account_lockout", fake_check_account_lockout)
        monkeypatch.setattr(auth_service, "log_auth_event", fake_log_auth_event)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(
                username="missing-user",
                password="Whatever123!",
                ip_address="127.0.0.1",
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.reason == "invalid_username"
        assert log_calls[0]["username"] == "missing-user"
        assert log_calls[0]["details"] == json.dumps({"reason": "invalid_username"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
