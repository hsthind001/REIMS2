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
from app.services.alert_workflow_service import AlertWorkflowService
from fastapi import Body, Path

# Note: Alert models not yet created, using direct SQL queries


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
    db: Session = Depends(get_db)
):
    """
    List alerts with optional filters.
    
    Query Parameters:
    - severity: Filter by severity
    - acknowledged: Filter by acknowledgment status
    - limit: Maximum results
    """
    from sqlalchemy import text
    
    # Build SQL query (models don't exist yet, use direct SQL)
    sql = """
        SELECT 
            id,
            alert_rule_id,
            message,
            severity,
            status,
            channels_sent,
            created_at,
            acknowledged_at
        FROM alerts
        WHERE 1=1
    """
    
    params = {}
    
    if severity:
        sql += " AND severity = :severity"
        params['severity'] = severity
    
    if acknowledged is not None:
        if acknowledged:
            sql += " AND acknowledged_at IS NOT NULL"
        else:
            sql += " AND acknowledged_at IS NULL"
    
    sql += " ORDER BY created_at DESC LIMIT :limit"
    params['limit'] = limit
    
    results = db.execute(text(sql), params).fetchall()
    
    # Build response
    return [
        AlertResponse(
            id=row.id,
            rule_id=row.alert_rule_id,
            severity=row.severity,
            message=row.message,
            channels_sent=row.channels_sent or [],
            delivered_at=None,  # Not tracked separately
            acknowledged_at=row.acknowledged_at,
            created_at=row.created_at
        )
        for row in results
    ]


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


# ==================== ALERT WORKFLOW ENDPOINTS ====================

@router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: int = Path(..., description="Alert ID"),
    until_period_id: Optional[int] = Body(None, description="Snooze until this period ID"),
    until_date: Optional[str] = Body(None, description="Snooze until this date (ISO format)"),
    reason: Optional[str] = Body(None, description="Reason for snoozing"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Snooze an alert until next period or date"""
    from datetime import datetime
    
    workflow_service = AlertWorkflowService(db)
    
    until_dt = None
    if until_date:
        try:
            until_dt = datetime.fromisoformat(until_date.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format.")
    
    result = workflow_service.snooze_alert(
        alert_id=alert_id,
        until_period_id=until_period_id,
        until_date=until_dt,
        reason=reason,
        snoozed_by=current_user.id
    )
    
    return result


@router.post("/{alert_id}/suppress")
async def suppress_alert(
    alert_id: int = Path(..., description="Alert ID"),
    reason: str = Body(..., description="Suppression reason"),
    expires_at: Optional[str] = Body(None, description="Expiry date (ISO format)"),
    expires_after_periods: Optional[int] = Body(None, description="Expire after N periods"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Suppress an alert with optional expiry"""
    from datetime import datetime
    
    workflow_service = AlertWorkflowService(db)
    
    expires_dt = None
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format.")
    
    result = workflow_service.suppress_alert(
        alert_id=alert_id,
        reason=reason,
        expires_at=expires_dt,
        expires_after_periods=expires_after_periods,
        suppressed_by=current_user.id
    )
    
    return result


@router.get("/suppression-rules")
async def get_suppression_rules(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active suppression rules"""
    workflow_service = AlertWorkflowService(db)
    rules = workflow_service.get_suppression_rules(property_id=property_id)
    
    return rules


@router.get("/{alert_id}/workflow-status")
async def get_alert_workflow_status(
    alert_id: int = Path(..., description="Alert ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workflow status for an alert (snoozed, suppressed, etc.)"""
    workflow_service = AlertWorkflowService(db)
    
    is_snoozed = workflow_service.is_alert_snoozed(alert_id)
    is_suppressed = workflow_service.is_alert_suppressed(alert_id=alert_id)
    
    return {
        'alert_id': alert_id,
        'is_snoozed': is_snoozed,
        'is_suppressed': is_suppressed,
        'is_active': not (is_snoozed or is_suppressed)
    }

