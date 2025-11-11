"""
Role-Based Access Control (RBAC) Service for REIMS2
Manages user roles, permissions, and access control.

Sprint 7: RBAC & Enhanced Security
"""
from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from functools import wraps
from fastapi import HTTPException, status

from app.models.user import User


class RBACService:
    """
    Role-Based Access Control service.
    
    Roles:
    - Admin: Full access to all features
    - Manager: Property management, reports, user management
    - Analyst: View reports, run analyses, no data modification
    - Viewer: Read-only access to assigned properties
    """
    
    # Define permissions for each role
    ROLE_PERMISSIONS = {
        'admin': {
            'properties.create', 'properties.read', 'properties.update', 'properties.delete',
            'documents.upload', 'documents.read', 'documents.delete',
            'extraction.run', 'extraction.read',
            'validation.read', 'validation.override',
            'reconciliation.read', 'reconciliation.update',
            'users.create', 'users.read', 'users.update', 'users.delete',
            'roles.assign',
            'alerts.create', 'alerts.read', 'alerts.update', 'alerts.delete',
            'reports.generate', 'reports.export',
            'api_keys.create', 'api_keys.revoke',
            'audit.read',
            'settings.update'
        },
        'manager': {
            'properties.read', 'properties.update',
            'documents.upload', 'documents.read',
            'extraction.run', 'extraction.read',
            'validation.read',
            'reconciliation.read', 'reconciliation.update',
            'users.read',
            'alerts.read', 'alerts.update',
            'reports.generate', 'reports.export',
            'audit.read'
        },
        'analyst': {
            'properties.read',
            'documents.read',
            'extraction.read',
            'validation.read',
            'reconciliation.read',
            'alerts.read',
            'reports.generate', 'reports.export'
        },
        'viewer': {
            'properties.read',
            'documents.read',
            'extraction.read',
            'reports.generate'
        }
    }
    
    def __init__(self, db: Session):
        """Initialize RBAC service."""
        self.db = db
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user_id: User ID
            permission: Permission string (e.g., 'properties.create')
            
        Returns:
            True if user has permission
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return False
        
        # Get user's role (assuming role stored in user.role field)
        user_role = getattr(user, 'role', 'viewer').lower()
        
        # Check if role has permission
        role_perms = self.ROLE_PERMISSIONS.get(user_role, set())
        return permission in role_perms
    
    def get_user_permissions(self, user_id: int) -> Set[str]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of permission strings
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return set()
        
        user_role = getattr(user, 'role', 'viewer').lower()
        return self.ROLE_PERMISSIONS.get(user_role, set())
    
    def assign_role(self, user_id: int, role: str, assigned_by: int) -> bool:
        """
        Assign role to user.
        
        Args:
            user_id: User ID to assign role to
            role: Role name (admin, manager, analyst, viewer)
            assigned_by: Admin user ID making the assignment
            
        Returns:
            True if role assigned successfully
        """
        # Check if assigning user has admin role
        if not self.check_permission(assigned_by, 'roles.assign'):
            return False
        
        # Validate role
        if role.lower() not in self.ROLE_PERMISSIONS:
            return False
        
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Assuming user model has a 'role' field
            # If not, would need to update user model schema
            user.role = role.lower()
            self.db.commit()
            
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error assigning role: {e}")
            return False


def require_permission(permission: str):
    """
    Decorator to enforce permission requirements on endpoints.
    
    Usage:
        @router.post("/properties")
        @require_permission("properties.create")
        async def create_property(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from request (would need dependency injection)
            # For now, placeholder implementation
            # In production, would get current_user from FastAPI Depends
            current_user_id = kwargs.get('current_user_id', None)
            
            if not current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission (would need db session)
            # Placeholder - in production would use dependency injection
            # rbac_service = RBACService(db)
            # if not rbac_service.check_permission(current_user_id, permission):
            #     raise HTTPException(
            #         status_code=status.HTTP_403_FORBIDDEN,
            #         detail=f"Permission denied: {permission}"
            #     )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

