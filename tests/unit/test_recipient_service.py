"""Unit tests for RecipientService."""

import pytest

from app.utils.validation import is_valid_email


class TestEmailValidation:
    """Test email validation logic."""
    
    def test_validate_email_valid(self):
        """Test validation accepts valid email addresses."""
        valid_emails = [
            "user@example.com",
            "john.doe@company.org",
            "test+tag@domain.co.uk",
            "admin@sub.domain.com",
            "user123@test.io",
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True
    
    def test_validate_email_invalid(self):
        """Test validation rejects invalid email addresses."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
            "",
            "user@domain",
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False
    
    def test_validate_email_edge_cases(self):
        """Test email validation edge cases."""
        # Email with numbers
        assert is_valid_email("user123@domain456.com") is True
        
        # Email with hyphens
        assert is_valid_email("user-name@my-domain.com") is True
        
        # Email with underscores
        assert is_valid_email("user_name@domain.com") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
