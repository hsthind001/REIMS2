"""
RBAC Management API Endpoints
Role-Based Access Control management for administrators.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Set, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.rbac_service import RBACService


router = APIRouter()


class RoleResponse(BaseModel):
    """Role response schema."""
    name: str
    description: Optional[str]
    permission_count: int


class PermissionResponse(BaseModel):
    """Permission response schema."""
    name: str
    resource: str
    action: str
    description: Optional[str]


class RoleAssignmentRequest(BaseModel):
    """Request to assign role to user."""
    role: str


class PermissionCheckRequest(BaseModel):
    """Request to check permission."""
    user_id: int
    permission: str


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available roles."""
    rbac_service = RBACService(db)
    
    roles = []
    for role_name, permissions in rbac_service.ROLE_PERMISSIONS.items():
        roles.append(RoleResponse(
            name=role_name,
            description=f"{role_name.title()} role",
            permission_count=len(permissions)
        ))
    
    return roles


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available permissions."""
    rbac_service = RBACService(db)
    
    # Collect all unique permissions
    all_permissions = set()
    for permissions in rbac_service.ROLE_PERMISSIONS.values():
        all_permissions.update(permissions)
    
    # Parse permission strings (format: resource.action)
    perm_list = []
    for perm in sorted(all_permissions):
        parts = perm.split('.')
        resource = parts[0] if len(parts) > 0 else perm
        action = parts[1] if len(parts) > 1 else 'unknown'
        
        perm_list.append(PermissionResponse(
            name=perm,
            resource=resource,
            action=action,
            description=f"{action.title()} {resource}"
        ))
    
    return perm_list


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: int,
    request: RoleAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a role to a user (admin only)."""
    rbac_service = RBACService(db)
    
    # Check if current user has permission
    if not rbac_service.check_permission(current_user.id, 'roles.assign'):
        raise HTTPException(status_code=403, detail="Permission denied: roles.assign required")
    
    # Assign role
    success = rbac_service.assign_role(
        user_id=user_id,
        role=request.role,
        assigned_by=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to assign role")
    
    return {
        "user_id": user_id,
        "role": request.role,
        "assigned_by": current_user.id,
        "assigned_at": datetime.utcnow().isoformat()
    }


@router.get("/users/{user_id}/permissions", response_model=List[str])
async def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all permissions for a specific user."""
    rbac_service = RBACService(db)
    permissions = rbac_service.get_user_permissions(user_id)
    return sorted(list(permissions))


@router.post("/check-permission")
async def check_permission(
    request: PermissionCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if a user has a specific permission."""
    rbac_service = RBACService(db)
    has_permission = rbac_service.check_permission(
        user_id=request.user_id,
        permission=request.permission
    )
    
    return {
        "user_id": request.user_id,
        "permission": request.permission,
        "has_permission": has_permission
    }


@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get RBAC audit logs"""
    # Return empty array for now, implement audit logging later
    return {"logs": [], "total": 0}

