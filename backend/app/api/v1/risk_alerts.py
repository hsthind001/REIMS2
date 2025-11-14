"""
Risk Alerts API Endpoints

Handles committee alerts, DSCR monitoring, and covenant compliance
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.db.database import get_db
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.services.committee_notification_service import CommitteeNotificationService
from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus, CommitteeType
from app.models.property import Property

router = APIRouter(prefix="/risk-alerts", tags=["risk_alerts"])
logger = logging.getLogger(__name__)


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: int


class AlertResolveRequest(BaseModel):
    resolved_by: int
    resolution_notes: str


class AlertDismissRequest(BaseModel):
    dismissed_by: int
    dismissal_reason: str


@router.post("/properties/{property_id}/dscr/calculate")
def calculate_dscr(
    property_id: int,
    financial_period_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Calculate DSCR for a property

    Returns DSCR value, NOI, debt service, and status
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DSCRMonitoringService(db)

    try:
        result = service.calculate_dscr(property_id, financial_period_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"DSCR calculation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/dscr/history")
def get_dscr_history(
    property_id: int,
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get DSCR history for a property (last N periods)
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DSCRMonitoringService(db)

    try:
        history = service.get_dscr_history(property_id, limit)

        return {
            "success": True,
            "property_id": property_id,
            "property_name": property.property_name,
            "history": history,
            "total_periods": len(history)
        }

    except Exception as e:
        logger.error(f"Failed to get DSCR history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/covenant-status")
def get_covenant_status(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get covenant compliance status for a property
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DSCRMonitoringService(db)

    try:
        result = service.get_covenant_status(property_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Failed to get covenant status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor-all-properties")
def monitor_all_properties(
    lookback_days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Monitor DSCR for all active properties

    Scans all properties and triggers alerts for violations
    """
    service = DSCRMonitoringService(db)

    try:
        result = service.monitor_all_properties(lookback_days)

        return {
            "success": True,
            "summary": result,
            "message": f"Monitored {result['total_properties']} properties"
        }

    except Exception as e:
        logger.error(f"Failed to monitor properties: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
def get_all_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    property_id: Optional[int] = None,
    committee: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get all alerts with optional filtering
    """
    query = db.query(CommitteeAlert)

    if status:
        query = query.filter(CommitteeAlert.status == status)

    if severity:
        query = query.filter(CommitteeAlert.severity == severity)

    if alert_type:
        query = query.filter(CommitteeAlert.alert_type == alert_type)

    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)

    if committee:
        query = query.filter(CommitteeAlert.assigned_committee == committee)

    alerts = query.order_by(
        CommitteeAlert.severity.desc(),
        CommitteeAlert.triggered_at.desc()
    ).limit(limit).all()

    return {
        "success": True,
        "alerts": [alert.to_dict() for alert in alerts],
        "total": len(alerts),
        "filters": {
            "status": status,
            "severity": severity,
            "alert_type": alert_type,
            "property_id": property_id,
            "committee": committee
        }
    }


@router.get("/alerts/{alert_id}")
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID
    """
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Get property details
    property = db.query(Property).filter(Property.id == alert.property_id).first()

    result = alert.to_dict()
    if property:
        result["property"] = {
            "id": property.id,
            "name": property.property_name,
            "code": property.property_code,
            "address": property.address,
        }

    return result


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert
    """
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status != AlertStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Alert is not active (current status: {alert.status.value})"
        )

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = request.acknowledged_by
    alert.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    logger.info(f"Alert {alert_id} acknowledged by user {request.acknowledged_by}")

    return {
        "success": True,
        "alert": alert.to_dict(),
        "message": "Alert acknowledged"
    }


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    request: AlertResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Resolve an alert
    """
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = request.resolved_by
    alert.resolution_notes = request.resolution_notes
    alert.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    # Send notification
    # notification_service = CommitteeNotificationService(db)
    # notification_service.notify_alert_resolved(alert, None)

    logger.info(f"Alert {alert_id} resolved by user {request.resolved_by}")

    return {
        "success": True,
        "alert": alert.to_dict(),
        "message": "Alert resolved"
    }


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: int,
    request: AlertDismissRequest,
    db: Session = Depends(get_db)
):
    """
    Dismiss an alert
    """
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.DISMISSED:
        raise HTTPException(status_code=400, detail="Alert is already dismissed")

    alert.status = AlertStatus.DISMISSED
    alert.dismissed_at = datetime.utcnow()
    alert.dismissed_by = request.dismissed_by
    alert.dismissal_reason = request.dismissal_reason
    alert.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    logger.info(f"Alert {alert_id} dismissed by user {request.dismissed_by}")

    return {
        "success": True,
        "alert": alert.to_dict(),
        "message": "Alert dismissed"
    }


@router.get("/properties/{property_id}/alerts")
def get_property_alerts(
    property_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all alerts for a specific property
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    query = db.query(CommitteeAlert).filter(CommitteeAlert.property_id == property_id)

    if status:
        query = query.filter(CommitteeAlert.status == status)

    alerts = query.order_by(CommitteeAlert.triggered_at.desc()).all()

    return {
        "success": True,
        "property_id": property_id,
        "property_name": property.property_name,
        "alerts": [alert.to_dict() for alert in alerts],
        "total": len(alerts)
    }


@router.get("/dashboard/summary")
def get_alert_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for alerts dashboard
    """
    total_alerts = db.query(CommitteeAlert).count()
    active_alerts = db.query(CommitteeAlert).filter(
        CommitteeAlert.status == AlertStatus.ACTIVE
    ).count()
    critical_alerts = db.query(CommitteeAlert).filter(
        CommitteeAlert.status == AlertStatus.ACTIVE,
        CommitteeAlert.severity.in_(['CRITICAL', 'URGENT'])
    ).count()

    # Alerts by committee
    alerts_by_committee = {}
    for committee in CommitteeType:
        count = db.query(CommitteeAlert).filter(
            CommitteeAlert.assigned_committee == committee,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).count()
        if count > 0:
            alerts_by_committee[committee.value] = count

    # Alerts by type
    alerts_by_type = {}
    for alert_type in AlertType:
        count = db.query(CommitteeAlert).filter(
            CommitteeAlert.alert_type == alert_type,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).count()
        if count > 0:
            alerts_by_type[alert_type.value] = count

    return {
        "success": True,
        "summary": {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "alerts_by_committee": alerts_by_committee,
            "alerts_by_type": alerts_by_type,
        }
    }
