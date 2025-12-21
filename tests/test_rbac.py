"""Tests for RBAC service and decorators."""

import pytest
from uuid import uuid4
from datetime import datetime

from app.services.rbac_service import rbac_service
from app.models import User


def create_test_user(role: str) -> User:
    """Helper to create a test user with specified role."""
    return User(
        id=uuid4(),
        username=f"test_{role}",
        password_hash="dummy_hash",
        full_name=f"Test {role.title()}",
        role=role,
        is_active=True,
        must_change_password=False,
        password_history=None,
        failed_login_count=0,
        locked_until=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestRBACService:
    """Test RBAC service functionality."""
    
    def test_can_manage_user_super_admin(self):
        """Super admin can manage anyone."""
        super_admin = create_test_user("super_admin")
        admin = create_test_user("admin")
        operator = create_test_user("operator")
        another_super_admin = create_test_user("super_admin")
        
        assert rbac_service.can_manage_user(super_admin, admin) is True
        assert rbac_service.can_manage_user(super_admin, operator) is True
        assert rbac_service.can_manage_user(super_admin, another_super_admin) is True
    
    def test_can_manage_user_admin(self):
        """Admin can only manage operators."""
        admin = create_test_user("admin")
        operator = create_test_user("operator")
        another_admin = create_test_user("admin")
        super_admin = create_test_user("super_admin")
        
        assert rbac_service.can_manage_user(admin, operator) is True
        assert rbac_service.can_manage_user(admin, another_admin) is False
        assert rbac_service.can_manage_user(admin, super_admin) is False
    
    def test_can_manage_user_operator(self):
        """Operator cannot manage anyone."""
        operator = create_test_user("operator")
        another_operator = create_test_user("operator")
        admin = create_test_user("admin")
        
        assert rbac_service.can_manage_user(operator, another_operator) is False
        assert rbac_service.can_manage_user(operator, admin) is False
    
    def test_can_create_user_with_role_super_admin(self):
        """Super admin can create any role."""
        super_admin = create_test_user("super_admin")
        
        assert rbac_service.can_create_user_with_role(super_admin, "super_admin") is True
        assert rbac_service.can_create_user_with_role(super_admin, "admin") is True
        assert rbac_service.can_create_user_with_role(super_admin, "operator") is True
    
    def test_can_create_user_with_role_admin(self):
        """Admin can only create operators."""
        admin = create_test_user("admin")
        
        assert rbac_service.can_create_user_with_role(admin, "operator") is True
        assert rbac_service.can_create_user_with_role(admin, "admin") is False
        assert rbac_service.can_create_user_with_role(admin, "super_admin") is False
    
    def test_can_create_user_with_role_operator(self):
        """Operator cannot create users."""
        operator = create_test_user("operator")
        
        assert rbac_service.can_create_user_with_role(operator, "operator") is False
        assert rbac_service.can_create_user_with_role(operator, "admin") is False
        assert rbac_service.can_create_user_with_role(operator, "super_admin") is False
    
    def test_get_user_permissions(self):
        """Test getting permissions for each role."""
        super_admin = create_test_user("super_admin")
        admin = create_test_user("admin")
        operator = create_test_user("operator")
        
        super_admin_perms = rbac_service.get_user_permissions(super_admin)
        admin_perms = rbac_service.get_user_permissions(admin)
        operator_perms = rbac_service.get_user_permissions(operator)
        
        # Super admin has all permissions
        assert "view_audit_logs" in super_admin_perms
        assert "manage_super_admin" in super_admin_perms
        assert "manage_users" in super_admin_perms
        
        # Admin has most permissions but not super admin ones
        assert "manage_users" in admin_perms
        assert "view_audit_logs" not in admin_perms
        assert "manage_super_admin" not in admin_perms
        
        # Operator has limited permissions
        assert "register_package" in operator_perms
        assert "view_packages" in operator_perms
        assert "manage_users" not in operator_perms
        assert "view_audit_logs" not in operator_perms
    
    def test_has_permission(self):
        """Test checking specific permissions."""
        super_admin = create_test_user("super_admin")
        admin = create_test_user("admin")
        operator = create_test_user("operator")
        
        # Test package permissions (all roles have)
        assert rbac_service.has_permission(super_admin, "register_package") is True
        assert rbac_service.has_permission(admin, "register_package") is True
        assert rbac_service.has_permission(operator, "register_package") is True
        
        # Test admin permissions
        assert rbac_service.has_permission(super_admin, "manage_users") is True
        assert rbac_service.has_permission(admin, "manage_users") is True
        assert rbac_service.has_permission(operator, "manage_users") is False
        
        # Test super admin only permissions
        assert rbac_service.has_permission(super_admin, "view_audit_logs") is True
        assert rbac_service.has_permission(admin, "view_audit_logs") is False
        assert rbac_service.has_permission(operator, "view_audit_logs") is False
    
    def test_is_higher_role(self):
        """Test role hierarchy comparison."""
        assert rbac_service.is_higher_role("super_admin", "admin") is True
        assert rbac_service.is_higher_role("super_admin", "operator") is True
        assert rbac_service.is_higher_role("admin", "operator") is True
        
        assert rbac_service.is_higher_role("operator", "admin") is False
        assert rbac_service.is_higher_role("admin", "super_admin") is False
        assert rbac_service.is_higher_role("operator", "super_admin") is False
        
        # Same role is not higher
        assert rbac_service.is_higher_role("admin", "admin") is False
    
    def test_can_modify_user_field(self):
        """Test field-level modification permissions."""
        super_admin = create_test_user("super_admin")
        admin = create_test_user("admin")
        operator = create_test_user("operator")
        
        # Super admin can modify any field of any user
        assert rbac_service.can_modify_user_field(super_admin, admin, "full_name") is True
        assert rbac_service.can_modify_user_field(super_admin, admin, "role") is True
        
        # Admin can modify operator fields except role
        assert rbac_service.can_modify_user_field(admin, operator, "full_name") is True
        assert rbac_service.can_modify_user_field(admin, operator, "role") is False
        
        # Admin cannot modify other admins
        another_admin = create_test_user("admin")
        assert rbac_service.can_modify_user_field(admin, another_admin, "full_name") is False
        
        # Operator cannot modify anyone
        assert rbac_service.can_modify_user_field(operator, operator, "full_name") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
