"""Role-Based Access Control (RBAC) service for permission management."""

from typing import Optional
from uuid import UUID

from app.models import User


class RBACService:
    """Service for managing role-based access control and permissions."""
    
    # Role hierarchy: super_admin > admin > operator
    ROLE_HIERARCHY = {
        "super_admin": 3,
        "admin": 2,
        "operator": 1,
    }
    
    # Permission mappings for each role
    ROLE_PERMISSIONS = {
        "super_admin": {
            # Super admin has all permissions
            "view_dashboard",
            "register_package",
            "update_package_status",
            "view_packages",
            "search_recipients",
            "manage_recipients",
            "import_recipients",
            "view_reports",
            "export_reports",
            "manage_users",
            "manage_admins",
            "view_audit_logs",
            "manage_super_admin",
        },
        "admin": {
            # Admin can do everything except manage super admins and view audit logs
            "view_dashboard",
            "register_package",
            "update_package_status",
            "view_packages",
            "search_recipients",
            "manage_recipients",
            "import_recipients",
            "view_reports",
            "export_reports",
            "manage_users",  # Can only manage operators
        },
        "operator": {
            # Operator can only handle packages
            "view_dashboard",
            "register_package",
            "update_package_status",
            "view_packages",
            "search_recipients",
        },
    }
    
    def can_manage_user(self, actor: User, target: User) -> bool:
        """
        Check if actor can manage (create, edit, deactivate) target user.
        
        Rules:
        - Super admin can manage anyone
        - Admin can manage operators only (not other admins or super admins)
        - Operators cannot manage anyone
        
        Args:
            actor: User attempting to perform the action
            target: User being managed
            
        Returns:
            True if actor can manage target, False otherwise
        """
        # Super admin can manage anyone
        if actor.role == "super_admin":
            return True
        
        # Admin can only manage operators
        if actor.role == "admin":
            return target.role == "operator"
        
        # Operators cannot manage anyone
        return False
    
    def can_create_user_with_role(self, actor: User, target_role: str) -> bool:
        """
        Check if actor can create a user with the specified role.
        
        Rules:
        - Super admin can create any role
        - Admin can only create operators
        - Operators cannot create users
        
        Args:
            actor: User attempting to create a new user
            target_role: Role for the new user
            
        Returns:
            True if actor can create user with target_role, False otherwise
        """
        # Super admin can create any role
        if actor.role == "super_admin":
            return True
        
        # Admin can only create operators
        if actor.role == "admin":
            return target_role == "operator"
        
        # Operators cannot create users
        return False
    
    def can_access_endpoint(self, user: User, endpoint: str) -> bool:
        """
        Check if user can access a specific endpoint based on their role.
        
        Args:
            user: User attempting to access the endpoint
            endpoint: Endpoint path or permission name
            
        Returns:
            True if user can access endpoint, False otherwise
        """
        # Get user's permissions
        permissions = self.get_user_permissions(user)
        
        # Check if user has the required permission
        return endpoint in permissions
    
    def get_user_permissions(self, user: User) -> set[str]:
        """
        Get all permissions for a user based on their role.
        
        Args:
            user: User to get permissions for
            
        Returns:
            Set of permission strings
        """
        return self.ROLE_PERMISSIONS.get(user.role, set())
    
    def has_permission(self, user: User, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user: User to check
            permission: Permission name to check
            
        Returns:
            True if user has permission, False otherwise
        """
        permissions = self.get_user_permissions(user)
        return permission in permissions
    
    def is_higher_role(self, role1: str, role2: str) -> bool:
        """
        Check if role1 is higher in hierarchy than role2.
        
        Args:
            role1: First role to compare
            role2: Second role to compare
            
        Returns:
            True if role1 is higher than role2, False otherwise
        """
        level1 = self.ROLE_HIERARCHY.get(role1, 0)
        level2 = self.ROLE_HIERARCHY.get(role2, 0)
        return level1 > level2
    
    def can_modify_user_field(
        self, 
        actor: User, 
        target: User, 
        field: str
    ) -> bool:
        """
        Check if actor can modify a specific field of target user.
        
        Some fields like 'role' have additional restrictions.
        
        Args:
            actor: User attempting to modify
            target: User being modified
            field: Field name being modified
            
        Returns:
            True if actor can modify the field, False otherwise
        """
        # First check if actor can manage target at all
        if not self.can_manage_user(actor, target):
            return False
        
        # Role changes have additional restrictions
        if field == "role":
            # Only super admin can change roles
            return actor.role == "super_admin"
        
        # For other fields, if they can manage the user, they can modify the field
        return True


# Global RBAC service instance
rbac_service = RBACService()
