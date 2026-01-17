"""
API dependencies for authentication and authorization

Supports both session-based and JWT-based authentication (BR-006)
Includes RBAC (Role-Based Access Control) decorator for endpoint protection
"""
from fastapi import Request, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from typing import Optional, Callable, List
from functools import wraps
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.organization import Organization


class UserRole(str, Enum):
    """User roles for RBAC"""
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPERUSER = "superuser"


# Role hierarchy: higher roles include all permissions of lower roles
ROLE_HIERARCHY = {
    UserRole.SUPERUSER: [UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ANALYST, UserRole.USER],
    UserRole.ADMIN: [UserRole.ADMIN, UserRole.ANALYST, UserRole.USER],
    UserRole.ANALYST: [UserRole.ANALYST, UserRole.USER],
    UserRole.USER: [UserRole.USER],
}


def get_user_role(user: User) -> UserRole:
    """
    Determine user's role based on their attributes.

    Role determination:
    - is_superuser=True -> SUPERUSER
    - is_admin=True (if field exists) -> ADMIN
    - Default -> USER
    """
    if user.is_superuser:
        return UserRole.SUPERUSER
    # Check for admin flag if it exists on the model
    if hasattr(user, 'is_admin') and user.is_admin:
        return UserRole.ADMIN
    # Check for role field if it exists
    if hasattr(user, 'role') and user.role:
        try:
            return UserRole(user.role)
        except ValueError:
            pass
    return UserRole.USER


def has_role(user: User, required_role: UserRole) -> bool:
    """
    Check if user has the required role (including via hierarchy).

    Args:
        user: The user to check
        required_role: The minimum required role

    Returns:
        True if user has the required role or higher
    """
    user_role = get_user_role(user)
    allowed_roles = ROLE_HIERARCHY.get(user_role, [])
    return required_role in allowed_roles


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory that requires user to have one of the specified roles.

    Usage:
        @router.delete("/delete-all")
        async def delete_all(
            current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPERUSER))
        ):
            ...

    Args:
        allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        A FastAPI dependency that validates user role
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role = get_user_role(current_user)

        # Check if user's role grants access to any of the allowed roles
        user_allowed_roles = ROLE_HIERARCHY.get(user_role, [])

        for role in allowed_roles:
            if role in user_allowed_roles:
                return current_user

        # User doesn't have any of the required roles
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {' or '.join(r.value for r in allowed_roles)}"
        )

    return dependency


def require_superuser():
    """
    Dependency that requires superuser access.

    Convenience wrapper for require_role(UserRole.SUPERUSER).
    """
    return require_role(UserRole.SUPERUSER)


def require_admin():
    """
    Dependency that requires admin or superuser access.

    Convenience wrapper for require_role(UserRole.ADMIN).
    """
    return require_role(UserRole.ADMIN, UserRole.SUPERUSER)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Get current authenticated user from session
    
    Used as a dependency in protected endpoints
    
    Args:
        request: FastAPI request with session
        db: Database session
    
    Returns:
        User: Current authenticated user
    
    Raises:
        HTTPException: If not authenticated or user not found
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
            headers={"WWW-Authenticate": "Session"}
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Session exists but user doesn't - clear session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Session cleared.",
            headers={"WWW-Authenticate": "Session"}
        )
    
    if not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (alias for get_current_user for compatibility)
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        User: Current authenticated and active user
    """
    return current_user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current user and verify they are a superuser
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        User: Current superuser
    
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superuser access required."
        )
    
    return current_user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Get current user if authenticated, or None if not
    
    Used for endpoints that can work with or without authentication
    
    Args:
        request: FastAPI request with session
        db: Database session
    
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        request.session.clear()
        return None
    
    return user


def get_current_user_jwt(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token (BR-006)
    
    Supports both Authorization header and query parameter:
    - Authorization: Bearer <token>
    - Query: ?token=<token>
    
    Used as a dependency in protected endpoints that support JWT
    
    Args:
        authorization: Authorization header value
        token: Token as query parameter (fallback)
        db: Database session
    
    Returns:
        User: Current authenticated user
    
    Raises:
        HTTPException: If not authenticated or user not found
    """
    from app.core.jwt_auth import get_jwt_service
    
    # Extract token from Authorization header
    jwt_token = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]
    elif token:
        jwt_token = token
    
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. JWT token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token and get user info
    jwt_service = get_jwt_service()
    user_info = jwt_service.get_user_from_token(jwt_token)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_info["user_id"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def get_current_user_hybrid(
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from either session or JWT token (BR-006)
    
    Tries JWT first, falls back to session-based auth.
    Supports both authentication methods for backward compatibility.
    
    Args:
        request: FastAPI request
        authorization: Authorization header (Bearer token)
        token: Token as query parameter
        db: Database session
    
    Returns:
        User: Current authenticated user
    """
    # Try JWT first
    jwt_token = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]
    elif token:
        jwt_token = token
    
    if jwt_token:
        try:
            return get_current_user_jwt(authorization=authorization, token=token, db=db)
        except HTTPException:
            pass  # Fall through to session auth
    
    # Fall back to session-based auth
    return get_current_user(request, db)


def get_current_organization(
    request: Request,
    organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> "Organization":
    """
    Get the current organization context from X-Organization-ID header.
    VALIDATES that the current user is a member of this organization.
    
    If no header is provided:
    - If user has only one organization, return it.
    - If user has multiple or none, raise 400 (Client must specify).
    
    Args:
        request: FastAPI request
        organization_id: ID from header
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Organization: The active organization object
    """
    from app.models.organization import Organization, OrganizationMember

    # 1. If explicit header provided
    if organization_id:
        try:
            org_id_int = int(organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Organization ID format"
            )
            
        # Check membership
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id_int
        ).first()
        
        if not membership:
             # Check if superuser (optional: allow superusers access to any org?)
             if current_user.is_superuser:
                 org = db.query(Organization).filter(Organization.id == org_id_int).first()
                 if not org:
                     raise HTTPException(status_code=404, detail="Organization not found")
                 return org
                 
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization"
            )
            
        return membership.organization

    # 2. No header provided - try to infer
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).all()
    
    if not memberships:
        # User belongs to NO organization
        # Allow if superuser, else error?
        # For SaaS, every user should be in an org. 
        # But newly signed up users might not be.
        # Return None or raise? 
        # For endpoints requiring an org, we should raise.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User belongs to no organization. Please create one."
        )
        
    if len(memberships) == 1:
        # Default to their only organization
        return memberships[0].organization
        
    # Multiple memberships - ambiguous
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Multiple organizations found. Please specify X-Organization-ID header."
    )
