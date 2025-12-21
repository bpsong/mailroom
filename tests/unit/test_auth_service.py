"""Unit tests for AuthService."""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.auth_service import auth_service
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
        assert "at least" in error_msg.lower()
        assert str(settings.password_min_length) in error_msg
    
    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        password = "testpassword123!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert "uppercase" in error_msg.lower()
    
    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        password = "TESTPASSWORD123!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert "lowercase" in error_msg.lower()
    
    def test_password_no_digit(self):
        """Test password without digit."""
        password = "TestPassword!"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
        assert "digit" in error_msg.lower()
    
    def test_password_no_special_char(self):
        """Test password without special character."""
        password = "TestPassword123"
        is_valid, error_msg = auth_service.validate_password_strength(password)
        
        assert is_valid is False
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
