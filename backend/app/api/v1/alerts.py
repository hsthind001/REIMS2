"""
Alert Management API Endpoints
Provides API access to alert rules and alert history.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.alert_service import AlertService


router = APIRouter()


class AlertRuleCreate(BaseModel):
    """Schema for creating alert rule."""
    name: str
    condition: str
    threshold: float
    channels: List[str]  # email, slack, in_app
    enabled: bool = True
    cooldown_minutes: int = 60


class AlertRuleResponse(BaseModel):
    """Alert rule response schema."""
    id: int
    name: str
    condition: str
    threshold: float
    channels: List[str]
    enabled: bool
    cooldown_minutes: int
    created_at: datetime


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: int
    rule_id: Optional[int]
    severity: str
    message: str
    channels_sent: List[str]
    delivered_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    created_at: datetime


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List alerts with optional filters.
    
    Query Parameters:
    - severity: Filter by severity
    - acknowledged: Filter by acknowledgment status
    - limit: Maximum results
    """
    # Would query alerts table
    return []


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific alert."""
    # Would query alerts table by ID
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new alert rule."""
    # Would insert into alert_rules table
    return AlertRuleResponse(
        id=1,
        name=rule.name,
        condition=rule.condition,
        threshold=rule.threshold,
        channels=rule.channels,
        enabled=rule.enabled,
        cooldown_minutes=rule.cooldown_minutes,
        created_at=datetime.utcnow()
    )


@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing alert rule."""
    # Would update alert_rules table
    return {"id": rule_id, "updated": True}


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an alert rule."""
    # Would delete from alert_rules table
    return {"id": rule_id, "deleted": True}


@router.post("/test")
async def test_alert(
    channels: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test alert delivery to specified channels."""
    alert_service = AlertService(db)
    
    results = alert_service.send_anomaly_alert(
        property_name="Test Property",
        anomaly_type="test",
        severity="low",
        message="This is a test alert",
        details={"test": True}
    )
    
    return {
        "channels_tested": channels,
        "delivery_status": results
    }

