"""
Notifications API Endpoints

Provides endpoints for managing user notifications.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: int
    type: str
    title: str
    message: str
    timestamp: str
    read: bool
    link: Optional[str] = None
    severity: str
    
    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    """Request model for marking notifications as read"""
    notification_ids: Optional[List[int]] = None  # If None, mark all as read


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notifications for the current user.
    
    Returns a list of notifications, optionally filtered to unread only.
    """
    try:
        query = db.query(Notification).filter(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        
        # Convert to response format
        result = []
        for notif in notifications:
            result.append(NotificationResponse(
                id=notif.id,
                type=notif.type,
                title=notif.title,
                message=notif.message,
                timestamp=notif.created_at.isoformat() if notif.created_at else datetime.utcnow().isoformat(),
                read=notif.read,
                link=notif.link,
                severity=notif.severity
            ))
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to fetch notifications for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}"
        )


@router.put("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read.
    """
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        if not notification.read_at:
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
        
        return {"success": True, "message": "Notification marked as read"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification {notification_id} as read: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.put("/read-all", response_model=dict)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications for the current user as read.
    """
    try:
        updated = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None)
        ).update({
            Notification.read_at: datetime.utcnow()
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Marked {updated} notifications as read"
        }
    
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read for user {current_user.id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the count of unread notifications for the current user.
    """
    try:
        count = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None)
        ).count()
        
        return {"unread_count": count}
    
    except Exception as e:
        logger.error(f"Failed to get unread count for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unread count: {str(e)}"
        )

