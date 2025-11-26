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
from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus, AlertSeverity, CommitteeType
from app.models.property import Property

router = APIRouter(prefix="/risk-alerts", tags=["risk_alerts"])
logger = logging.getLogger(__name__)


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: int
    email: Optional[str] = None
    notes: Optional[str] = None


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
    Acknowledge an alert and optionally send email notification
    """
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status != AlertStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Alert is not active (current status: {alert.status.value})"
        )

    # Update alert status
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = request.acknowledged_by
    alert.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    logger.info(f"Alert {alert_id} acknowledged by user {request.acknowledged_by}")

    # Send email if provided
    email_sent = False
    email_error = None
    development_mode = False
    if request.email:
        try:
            from app.services.committee_notification_service import CommitteeNotificationService
            notification_service = CommitteeNotificationService(db)
            
            # Get comprehensive alert details for email
            email_result = notification_service.send_alert_acknowledgment_email(
                alert=alert,
                recipient_email=request.email
            )
            
            if email_result.get("success"):
                email_sent = True
                development_mode = email_result.get("development_mode", False)
                if development_mode:
                    logger.info(f"Alert acknowledgment email logged (development mode) for {request.email}")
                else:
                    logger.info(f"Alert acknowledgment email sent to {request.email}")
            else:
                email_error = email_result.get("error", "Unknown error")
                logger.warning(f"Failed to send acknowledgment email: {email_error}")
        except Exception as e:
            email_error = str(e)
            logger.error(f"Exception sending acknowledgment email: {str(e)}", exc_info=True)

    return {
        "success": True,
        "alert": alert.to_dict(),
        "message": "Alert acknowledged",
        "email_sent": email_sent,
        "email_error": email_error,
        "development_mode": development_mode
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
    Queries both the alerts table and committee_alerts table
    """
    from sqlalchemy import text
    
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Query alerts table (the main alerts system)
    sql = """
        SELECT 
            a.id,
            a.alert_rule_id,
            a.anomaly_detection_id,
            a.document_id,
            a.message,
            a.severity,
            a.status,
            a.created_at,
            a.acknowledged_at,
            a.acknowledged_by,
            a.resolved_at,
            a.resolved_by,
            du.file_name,
            du.document_type,
            ar.rule_name,
            ar.field_name,
            ar.threshold_value
        FROM alerts a
        JOIN document_uploads du ON a.document_id = du.id
        LEFT JOIN alert_rules ar ON a.alert_rule_id = ar.id
        WHERE du.property_id = :property_id
    """
    
    params = {'property_id': property_id}
    
    if status:
        sql += " AND a.status = :status"
        params['status'] = status
    
    sql += " ORDER BY a.created_at DESC"
    
    results = db.execute(text(sql), params).fetchall()
    
    # Convert to dict format matching frontend expectations
    alerts_list = []
    for row in results:
        # Extract alert type from message or rule name
        alert_type = row.rule_name or 'threshold_breach'
        if 'occupancy' in row.message.lower():
            alert_type = 'occupancy_warning'
        elif 'debt' in row.message.lower() or 'equity' in row.message.lower():
            alert_type = 'covenant_violation'
        elif 'current ratio' in row.message.lower() or 'liquidity' in row.message.lower():
            alert_type = 'financial_threshold'
        
        # Extract threshold and actual values from message
        threshold_value = float(row.threshold_value) if row.threshold_value else None
        actual_value = None
        
        # Try to extract actual value from message (e.g., "84.00%" or "0.24" or "469.86")
        import re
        # Look for patterns like "is 84.00%" or "is 0.24" or "ratio is 469.86"
        # Match number after "is " or "ratio is " or similar patterns
        value_patterns = [
            r'is\s+(\d+\.?\d*)',  # "is 84.00" or "is 0.24"
            r'rate\s+is\s+(\d+\.?\d*)',  # "rate is 84.00"
            r'ratio\s+is\s+(\d+\.?\d*)',  # "ratio is 469.86"
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, row.message, re.IGNORECASE)
            if match:
                try:
                    actual_value = float(match.group(1))
                    break
                except:
                    pass
        
        # Fallback: if no pattern match, try to find the first significant number
        if actual_value is None:
            numbers = re.findall(r'\d+\.?\d+', row.message)  # Match numbers with decimals
            if numbers:
                try:
                    # Use the first number that's not the threshold
                    for num_str in numbers:
                        num = float(num_str)
                        if threshold_value and abs(num - threshold_value) > 0.1:  # Not the threshold
                            actual_value = num
                            break
                        elif not threshold_value:
                            actual_value = num
                            break
                except:
                    pass
        
        alerts_list.append({
            "id": row.id,
            "property_id": property_id,
            "alert_type": alert_type,
            "severity": row.severity,
            "status": row.status or "active",
            "title": row.message.split(':')[0] if ':' in row.message else row.message[:50],
            "description": row.message,
            "threshold_value": threshold_value,
            "actual_value": actual_value,
            "threshold_unit": "ratio" if "ratio" in row.message.lower() else "percentage" if "%" in row.message else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "acknowledged_by": row.acknowledged_by,
            "resolved_by": row.resolved_by,
            "document_id": row.document_id,
            "file_name": row.file_name,
            "document_type": row.document_type,
            "field_name": row.field_name
        })
    
    # Also query committee_alerts for completeness
    committee_alerts = db.query(CommitteeAlert).filter(CommitteeAlert.property_id == property_id)
    if status:
        committee_alerts = committee_alerts.filter(CommitteeAlert.status == status)
    committee_alerts = committee_alerts.order_by(CommitteeAlert.triggered_at.desc()).all()
    
    # Add committee alerts to the list with file information
    for alert in committee_alerts:
        alert_dict = alert.to_dict()
        
        # Get period information
        if alert.financial_period_id:
            from app.models.financial_period import FinancialPeriod
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == alert.financial_period_id
            ).first()
            if period:
                alert_dict["period_year"] = period.period_year
                alert_dict["period_month"] = period.period_month
                alert_dict["period"] = f"{period.period_year}-{str(period.period_month).zfill(2)}"
        
        # Try to get file information from financial_period_id
        if alert.financial_period_id and not alert_dict.get("file_name"):
            from app.models.document_upload import DocumentUpload
            # Look for document uploads for this property and period
            uploads = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == alert.property_id,
                DocumentUpload.period_id == alert.financial_period_id
            ).order_by(DocumentUpload.upload_date.desc()).all()
            
            # Prefer income statement for DSCR alerts, otherwise use most recent
            for upload in uploads:
                if upload.document_type == 'income_statement' or (alert.alert_type.value == 'DSCR_BREACH' and upload.document_type == 'income_statement'):
                    alert_dict["file_name"] = upload.file_name
                    alert_dict["document_type"] = upload.document_type
                    alert_dict["document_id"] = upload.id
                    break
            
            # If no income statement, use most recent document
            if not alert_dict.get("file_name") and uploads:
                alert_dict["file_name"] = uploads[0].file_name
                alert_dict["document_type"] = uploads[0].document_type
                alert_dict["document_id"] = uploads[0].id
        
        alerts_list.append(alert_dict)
    
    return {
        "success": True,
        "property_id": property_id,
        "property_name": property.property_name,
        "alerts": alerts_list,
        "total": len(alerts_list)
    }


@router.get("/dashboard/summary")
def get_alert_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for alerts dashboard
    Queries both alerts table and committee_alerts table
    """
    from sqlalchemy import text
    
    # Query alerts table (main alerts system)
    alerts_sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as active,
            COUNT(*) FILTER (WHERE status = 'active' AND severity IN ('critical', 'urgent')) as critical
        FROM alerts a
        JOIN document_uploads du ON a.document_id = du.id
    """
    alerts_stats = db.execute(text(alerts_sql)).fetchone()
    
    # Query committee_alerts
    total_committee_alerts = db.query(CommitteeAlert).count()
    active_committee_alerts = db.query(CommitteeAlert).filter(
        CommitteeAlert.status == AlertStatus.ACTIVE
    ).count()
    critical_committee_alerts = db.query(CommitteeAlert).filter(
        CommitteeAlert.status == AlertStatus.ACTIVE,
        CommitteeAlert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.URGENT])
    ).count()
    
    # Combine counts
    total_alerts = (alerts_stats.total or 0) + total_committee_alerts
    active_alerts = (alerts_stats.active or 0) + active_committee_alerts
    critical_alerts = (alerts_stats.critical or 0) + critical_committee_alerts
    
    # Count properties with good DSCR (properties with DSCR >= 1.2)
    properties_with_good_dscr_sql = """
        SELECT COUNT(DISTINCT p.id)
        FROM properties p
        JOIN financial_periods fp ON p.id = fp.property_id
        JOIN financial_metrics fm ON fp.id = fm.period_id
        WHERE fm.dscr >= 1.2
        AND p.status = 'active'
    """
    good_dscr_count = db.execute(text(properties_with_good_dscr_sql)).scalar() or 0
    
    # Count active workflow locks
    from app.models.workflow_lock import WorkflowLock, LockStatus
    active_locks = db.query(WorkflowLock).filter(
        WorkflowLock.status == LockStatus.ACTIVE
    ).count()

    # Alerts by committee (from committee_alerts only)
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
        "total_critical_alerts": critical_alerts,
        "total_active_alerts": active_alerts,
        "total_active_locks": active_locks,
        "properties_with_good_dscr": good_dscr_count,
        "summary": {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "active_locks": active_locks,
            "properties_with_good_dscr": good_dscr_count,
            "alerts_by_committee": alerts_by_committee,
            "alerts_by_type": alerts_by_type,
        }
    }
