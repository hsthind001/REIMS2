"""
API dependencies for authentication and authorization

Supports both session-based and JWT-based authentication (BR-006)
"""
from fastapi import Request, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from typing import Optional


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
