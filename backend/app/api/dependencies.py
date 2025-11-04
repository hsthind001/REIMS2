"""
API dependencies for authentication and authorization
"""
from fastapi import Request, HTTPException, status, Depends
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
