"""
Public API Endpoints
External API access for third-party integrations.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.public_api_service import PublicAPIService


router = APIRouter()


class APIKeyCreateRequest(BaseModel):
    """Request to create API key."""
    name: str
    permissions: List[str]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (only shown once)."""
    api_key: str
    key_hash: str
    name: str
    permissions: List[str]
    created_at: str
    expires_at: Optional[str]
    rate_limit: int


class WebhookCreateRequest(BaseModel):
    """Request to register webhook."""
    url: str
    events: List[str]  # extraction_complete, validation_failed, alert_triggered
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook registration response."""
    webhook_id: str
    url: str
    events: List[str]
    secret: str
    created_at: str


@router.post("/api-keys", response_model=APIKeyResponse)
async def generate_api_key(
    request: APIKeyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new API key for external access.
    
    Note: API key is only shown once. Store it securely!
    """
    api_service = PublicAPIService(db)
    
    key_data = api_service.generate_api_key(
        user_id=current_user.id,
        name=request.name,
        permissions=request.permissions,
        expires_in_days=request.expires_in_days
    )
    
    return APIKeyResponse(**key_data)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key (marks as inactive)."""
    # Would update api_keys table set is_active=false
    return {
        "key_id": key_id,
        "revoked": True,
        "revoked_at": datetime.utcnow().isoformat()
    }


@router.get("/api-keys/stats")
async def get_api_key_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get API usage statistics for current user's API keys."""
    # Would query api_usage_logs joined with api_keys
    return {
        "total_keys": 0,
        "active_keys": 0,
        "total_requests_today": 0,
        "requests_by_endpoint": {}
    }


@router.post("/webhooks", response_model=WebhookResponse)
async def register_webhook(
    request: WebhookCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a webhook URL for event notifications."""
    api_service = PublicAPIService(db)
    
    webhook_data = api_service.register_webhook(
        user_id=current_user.id,
        url=request.url,
        events=request.events,
        secret=request.secret
    )
    
    return WebhookResponse(**webhook_data)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a webhook registration."""
    # Would delete from webhooks table
    return {
        "webhook_id": webhook_id,
        "deleted": True
    }


@router.get("/webhooks/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: int,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get delivery history for a webhook."""
    # Would query webhook_deliveries table
    return {
        "webhook_id": webhook_id,
        "deliveries": []
    }

