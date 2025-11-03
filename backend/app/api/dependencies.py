"""
API Dependencies
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User


async def get_current_user(db: Session = Depends(get_db)) -> User:
    """
    Get current authenticated user.
    
    For Sprint 1.2, we'll use a mock user since authentication is not yet implemented.
    In future sprints, this will be replaced with actual JWT token validation.
    """
    # TODO: Replace with actual authentication in future sprint
    # For now, return a default system user
    user = db.query(User).filter(User.username == "system").first()
    
    if not user:
        # Create default system user if doesn't exist
        user = User(
            username="system",
            email="system@reims.local",
            hashed_password="not_used",
            is_active=True,
            is_superuser=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user

