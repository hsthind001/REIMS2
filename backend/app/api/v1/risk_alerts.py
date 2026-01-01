"""
Risk Alerts API Endpoints

Handles committee alerts, DSCR monitoring, and covenant compliance
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.db.database import get_db
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.services.committee_notification_service import CommitteeNotificationService
from app.services.alert_correlation_service import AlertCorrelationService
from app.services.alert_escalation_service import AlertEscalationService
from app.services.alert_prioritization_service import AlertPrioritizationService
from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus, AlertSeverity, CommitteeType
from app.models.property import Property
from app.models.user import User
from app.models.income_statement_data import IncomeStatementData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.models.financial_metrics import FinancialMetrics
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/risk-alerts", tags=["risk_alerts"])
logger = logging.getLogger(__name__)


def _has_financial_data_for_period(db: Session, property_id: int, period_id: int) -> bool:
    """
    Check if property has actual uploaded financial documents for the period
    
    Returns True if property has:
    - Income statement data, OR
    - Mortgage statement data, OR
    - Document uploads with extraction_status='completed'
    """
    # Check for income statement data
    income_data = db.query(IncomeStatementData).filter(
        IncomeStatementData.property_id == property_id,
        IncomeStatementData.period_id == period_id
    ).first()
    
    if income_data:
        return True
    
    # Check for mortgage statement data
    mortgage_data = db.query(MortgageStatementData).filter(
        MortgageStatementData.property_id == property_id,
        MortgageStatementData.period_id == period_id
    ).first()
    
    if mortgage_data:
        return True
    
    # Check for completed document uploads
    completed_upload = db.query(DocumentUpload).filter(
        DocumentUpload.property_id == property_id,
        DocumentUpload.period_id == period_id,
        DocumentUpload.extraction_status == 'completed'
    ).first()
    
    if completed_upload:
        return True
    
    return False


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
    financial_period_id: Optional[int] = Query(None, description="Financial period ID"),
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
            # Return error response instead of raising exception to allow frontend to handle gracefully
            return {
                "success": False,
                "error": result.get("error", "DSCR calculation failed"),
                "property_id": property_id,
                "financial_period_id": financial_period_id,
                "dscr": None,
                "noi": None,
                "total_debt_service": None,
                "status": "error"
            }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DSCR calculation failed for property {property_id}: {str(e)}", exc_info=True)
        # Return error response instead of raising 500 to allow frontend to handle
        return {
            "success": False,
            "error": f"DSCR calculation failed: {str(e)}",
            "property_id": property_id,
            "financial_period_id": financial_period_id,
            "dscr": None,
            "noi": None,
            "total_debt_service": None,
            "status": "error"
        }


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


@router.get("/diagnostics/duplicate-alerts")
def diagnose_duplicate_alerts(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (e.g., DSCR_BREACH)"),
    db: Session = Depends(get_db)
):
    """
    Diagnostic endpoint to analyze duplicate alerts
    
    Identifies:
    - Alerts for same property/period combination
    - Different periods vs same period duplicates
    - Status distribution of duplicates
    """
    from sqlalchemy import func, case
    from app.models.financial_period import FinancialPeriod
    
    # Build base query
    query = db.query(CommitteeAlert)
    
    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)
    
    if alert_type:
        query = query.filter(CommitteeAlert.alert_type == alert_type)
    else:
        # Default to DSCR_BREACH for this diagnostic
        query = query.filter(CommitteeAlert.alert_type == AlertType.DSCR_BREACH)
    
    alerts = query.order_by(
        CommitteeAlert.property_id,
        CommitteeAlert.financial_period_id,
        CommitteeAlert.triggered_at.desc()
    ).all()
    
    # Group alerts by property/period
    alert_groups = {}
    for alert in alerts:
        key = (alert.property_id, alert.financial_period_id)
        if key not in alert_groups:
            alert_groups[key] = []
        alert_groups[key].append({
            "id": alert.id,
            "status": alert.status.value if alert.status else None,
            "severity": alert.severity.value if alert.severity else None,
            "actual_value": float(alert.actual_value) if alert.actual_value else None,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        })
    
    # Find duplicates (more than 1 alert per property/period)
    duplicates = {}
    for key, alert_list in alert_groups.items():
        if len(alert_list) > 1:
            property_id_val, period_id_val = key
            
            # Get period details
            period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id_val).first()
            period_info = None
            if period:
                period_info = {
                    "year": period.period_year,
                    "month": period.period_month,
                    "start_date": period.period_start_date.isoformat() if period.period_start_date else None,
                    "end_date": period.period_end_date.isoformat() if period.period_end_date else None,
                }
            
            # Get property details
            property_obj = db.query(Property).filter(Property.id == property_id_val).first()
            property_info = None
            if property_obj:
                property_info = {
                    "id": property_obj.id,
                    "name": property_obj.property_name,
                    "code": property_obj.property_code,
                }
            
            duplicates[key] = {
                "property": property_info,
                "period": period_info,
                "period_id": period_id_val,
                "alert_count": len(alert_list),
                "alerts": alert_list,
                "statuses": list(set(a["status"] for a in alert_list)),
                "active_count": sum(1 for a in alert_list if a["status"] == "ACTIVE"),
                "acknowledged_count": sum(1 for a in alert_list if a["status"] == "ACKNOWLEDGED"),
                "resolved_count": sum(1 for a in alert_list if a["status"] == "RESOLVED"),
            }
    
    # Summary statistics
    total_alerts = len(alerts)
    total_property_period_combinations = len(alert_groups)
    total_duplicates = len(duplicates)
    total_duplicate_alerts = sum(len(v["alerts"]) for v in duplicates.values())
    
    return {
        "success": True,
        "summary": {
            "total_alerts": total_alerts,
            "total_property_period_combinations": total_property_period_combinations,
            "total_duplicate_groups": total_duplicates,
            "total_duplicate_alerts": total_duplicate_alerts,
            "unique_alerts": total_alerts - total_duplicate_alerts + total_duplicates,
        },
        "duplicates": duplicates,
        "message": f"Found {total_duplicates} property/period combinations with duplicate alerts"
    }


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


@router.post("/properties/{property_id}/trigger-alerts")
def trigger_alerts_for_property(
    property_id: int,
    period_id: Optional[int] = Query(None, description="Financial period ID. If not provided, uses latest period"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger alert evaluation for a property
    
    Evaluates all active alert rules against current financial metrics
    and creates alerts when thresholds are breached.
    """
    from app.services.alert_trigger_service import AlertTriggerService
    from app.models.financial_metrics import FinancialMetrics
    from app.models.property import Property
    
    # Verify property exists
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get period_id if not provided
    if not period_id:
        from app.models.financial_period import FinancialPeriod
        latest_period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc()).first()
        
        if not latest_period:
            raise HTTPException(status_code=404, detail="No financial periods found for this property")
        period_id = latest_period.id
    
    try:
        # Get metrics for this property/period
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if not metrics:
            raise HTTPException(
                status_code=404, 
                detail=f"No financial metrics found for property {property_id}, period {period_id}. "
                       "Please calculate metrics first."
            )
        
        # Trigger alert evaluation
        alert_service = AlertTriggerService(db)
        created_alerts = alert_service.evaluate_and_trigger_alerts(
            property_id=property_id,
            period_id=period_id,
            metrics=metrics
        )
        
        return {
            "success": True,
            "property_id": property_id,
            "period_id": period_id,
            "alerts_created": len(created_alerts),
            "alerts": created_alerts,
            "message": f"Triggered {len(created_alerts)} alert(s) for property {property_id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger alerts for property {property_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger alerts: {str(e)}")


@router.post("/backfill-alerts")
def backfill_alerts(
    start_year: int = Query(..., ge=2000, le=2100),
    start_month: int = Query(..., ge=1, le=12),
    end_year: int = Query(..., ge=2000, le=2100),
    end_month: int = Query(..., ge=1, le=12),
    property_id: Optional[int] = Query(None),
    ignore_cooldown: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Backfill alerts for a date range (YYYY-MM to YYYY-MM).

    Evaluates alert rules for each property/period that has metrics in the range.
    """
    if (end_year, end_month) < (start_year, start_month):
        raise HTTPException(status_code=400, detail="End period must be >= start period")

    from app.services.alert_trigger_service import AlertTriggerService

    period_query = db.query(FinancialPeriod, FinancialMetrics).join(
        FinancialMetrics, FinancialMetrics.period_id == FinancialPeriod.id
    )

    if property_id:
        period_query = period_query.filter(FinancialPeriod.property_id == property_id)

    period_query = period_query.filter(
        or_(
            FinancialPeriod.period_year > start_year,
            and_(
                FinancialPeriod.period_year == start_year,
                FinancialPeriod.period_month >= start_month
            )
        ),
        or_(
            FinancialPeriod.period_year < end_year,
            and_(
                FinancialPeriod.period_year == end_year,
                FinancialPeriod.period_month <= end_month
            )
        )
    ).order_by(
        FinancialPeriod.property_id,
        FinancialPeriod.period_year,
        FinancialPeriod.period_month
    )

    results = []
    total_alerts = 0
    trigger_service = AlertTriggerService(db)
    period_rows = period_query.all()

    for period, metrics in period_rows:
        alerts = trigger_service.evaluate_and_trigger_alerts(
            property_id=period.property_id,
            period_id=period.id,
            metrics=metrics,
            ignore_cooldown=ignore_cooldown
        )
        if alerts:
            results.append({
                "property_id": period.property_id,
                "period_id": period.id,
                "period_year": period.period_year,
                "period_month": period.period_month,
                "alerts_created": len(alerts)
            })
        total_alerts += len(alerts)

    return {
        "success": True,
        "property_id": property_id,
        "start_period": f"{start_year}-{start_month:02d}",
        "end_period": f"{end_year}-{end_month:02d}",
        "periods_evaluated": len(period_rows),
        "alerts_created": total_alerts,
        "results": results
    }


@router.get("")
@router.get("/")
def get_risk_alerts(
    priority: Optional[str] = Query(None, description="Filter by priority (critical, high, medium, low)"),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    property_id: Optional[int] = None,
    committee: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get all risk alerts with optional filtering
    Supports both /risk-alerts?priority=critical and /risk-alerts/alerts?severity=critical
    """
    # Map priority to severity if provided
    if priority:
        priority_map = {
            'critical': AlertSeverity.CRITICAL,
            'high': AlertSeverity.CRITICAL,
            'medium': AlertSeverity.WARNING,
            'low': AlertSeverity.INFO
        }
        severity = priority_map.get(priority.lower(), severity)

    query = db.query(CommitteeAlert).options(joinedload(CommitteeAlert.property))

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

    # Enhance alert data with property details and metric information
    alerts_data = []
    for alert in alerts:
        alert_dict = alert.to_dict()
        
        # Add property details if property relationship is loaded
        if alert.property:
            alert_dict["property_name"] = alert.property.property_name
            alert_dict["property_code"] = alert.property.property_code
            
            # For DSCR alerts, check if property has actual financial data
            # Skip alerts for properties without uploaded documents
            if alert.alert_type == AlertType.DSCR_BREACH and alert.financial_period_id:
                has_data = _has_financial_data_for_period(db, alert.property_id, alert.financial_period_id)
                if not has_data:
                    logger.debug(
                        f"Skipping DSCR alert {alert.id} for property {alert.property_id}: "
                        "No financial data uploaded"
                    )
                    continue  # Skip this alert
        
        # Add period information if financial_period_id exists
        if alert.financial_period_id:
            from app.models.financial_period import FinancialPeriod
            period = db.query(FinancialPeriod).filter(FinancialPeriod.id == alert.financial_period_id).first()
            if period:
                alert_dict["period"] = {
                    "id": period.id,
                    "year": period.period_year,
                    "month": period.period_month,
                    "start_date": period.period_start_date.isoformat() if period.period_start_date else None,
                    "end_date": period.period_end_date.isoformat() if period.period_end_date else None,
                }
        
        # Map metric name from related_metric or alert_type
        alert_dict["metric_name"] = alert.related_metric or (alert.alert_type.value if alert.alert_type else "Unknown")
        
        # Add impact and recommendation from metadata or description
        if alert.alert_metadata and isinstance(alert.alert_metadata, dict):
            alert_dict["impact"] = alert.alert_metadata.get("impact", "Risk identified")
        else:
            alert_dict["impact"] = "Risk identified"
        
        # Use description as recommendation, or default message
        alert_dict["recommendation"] = alert.description or "Review immediately"
        
        alerts_data.append(alert_dict)

    return {
        "success": True,
        "alerts": alerts_data,
        "total": len(alerts_data),
        "filters": {
            "priority": priority,
            "status": status,
            "severity": severity,
            "alert_type": alert_type,
            "property_id": property_id,
            "committee": committee
        }
    }


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
    query = db.query(CommitteeAlert).options(joinedload(CommitteeAlert.property))

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

    # Enhance alert data with property details and metric information
    # Also filter out alerts for properties without uploaded financial data
    alerts_data = []
    for alert in alerts:
        alert_dict = alert.to_dict()
        
        # Add property details if property relationship is loaded
        if alert.property:
            alert_dict["property_name"] = alert.property.property_name
            alert_dict["property_code"] = alert.property.property_code
            
            # For DSCR alerts, check if property has actual financial data
            # Skip alerts for properties without uploaded documents
            if alert.alert_type == AlertType.DSCR_BREACH and alert.financial_period_id:
                has_data = _has_financial_data_for_period(db, alert.property_id, alert.financial_period_id)
                if not has_data:
                    logger.debug(
                        f"Skipping DSCR alert {alert.id} for property {alert.property_id}: "
                        "No financial data uploaded"
                    )
                    continue  # Skip this alert
        
        # Add period information if financial_period_id exists
        if alert.financial_period_id:
            from app.models.financial_period import FinancialPeriod
            period = db.query(FinancialPeriod).filter(FinancialPeriod.id == alert.financial_period_id).first()
            if period:
                alert_dict["period"] = {
                    "id": period.id,
                    "year": period.period_year,
                    "month": period.period_month,
                    "start_date": period.period_start_date.isoformat() if period.period_start_date else None,
                    "end_date": period.period_end_date.isoformat() if period.period_end_date else None,
                }
        
        # Map metric name from related_metric or alert_type
        alert_dict["metric_name"] = alert.related_metric or (alert.alert_type.value if alert.alert_type else "Unknown")
        
        # Add impact and recommendation from metadata or description
        if alert.alert_metadata and isinstance(alert.alert_metadata, dict):
            alert_dict["impact"] = alert.alert_metadata.get("impact", "Risk identified")
        else:
            alert_dict["impact"] = "Risk identified"
        
        # Use description as recommendation, or default message
        alert_dict["recommendation"] = alert.description or "Review immediately"
        
        alerts_data.append(alert_dict)

    return {
        "success": True,
        "alerts": alerts_data,
        "total": len(alerts_data),
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

    try:
        # Query alerts table (the main alerts system)
        # Use LEFT JOIN to include alerts even if document_uploads doesn't exist
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
            LEFT JOIN document_uploads du ON a.document_id = du.id
            LEFT JOIN alert_rules ar ON a.alert_rule_id = ar.id
            WHERE du.property_id = :property_id
        """
        
        params = {'property_id': property_id}
        
        if status:
            sql += " AND a.status = :status"
            params['status'] = status
        
        sql += " ORDER BY a.created_at DESC"
        
        results = db.execute(text(sql), params).fetchall()
    except Exception as e:
        # If alerts table doesn't exist or query fails, log error and continue with committee_alerts only
        logger.warning(f"Failed to query alerts table: {str(e)}, falling back to committee_alerts only")
        logger.debug(f"Alerts table query error details: {type(e).__name__}: {str(e)}", exc_info=True)
        results = []
    
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
    # Use raw SQL to avoid model column mismatch issues
    from sqlalchemy import text as sql_text
    committee_sql = """
        SELECT 
            id,
            property_id,
            financial_period_id,
            alert_type,
            severity,
            status,
            title,
            description,
            threshold_value,
            actual_value,
            threshold_unit,
            assigned_committee,
            requires_approval,
            triggered_at,
            acknowledged_at,
            resolved_at,
            dismissed_at,
            acknowledged_by,
            resolved_by,
            dismissed_by,
            resolution_notes,
            dismissal_reason,
            metadata as alert_metadata,
            related_metric,
            br_id,
            created_at,
            updated_at
        FROM committee_alerts
        WHERE property_id = :property_id
    """
    committee_params = {'property_id': property_id}
    if status:
        committee_sql += " AND status = :status"
        committee_params['status'] = status
    committee_sql += " ORDER BY triggered_at DESC"
    
    committee_results = db.execute(sql_text(committee_sql), committee_params).fetchall()
    
    # Add committee alerts to the list with file information
    for row in committee_results:
        # Convert to dict format matching frontend expectations
        alert_dict = {
            "id": row.id,
            "property_id": row.property_id,
            "financial_period_id": row.financial_period_id,
            "alert_type": row.alert_type.value if hasattr(row.alert_type, 'value') else str(row.alert_type),
            "severity": row.severity.value if hasattr(row.severity, 'value') else str(row.severity),
            "status": row.status.value if hasattr(row.status, 'value') else str(row.status),
            "title": row.title,
            "description": row.description,
            "threshold_value": float(row.threshold_value) if row.threshold_value else None,
            "actual_value": float(row.actual_value) if row.actual_value else None,
            "threshold_unit": row.threshold_unit,
            "assigned_committee": row.assigned_committee.value if hasattr(row.assigned_committee, 'value') else str(row.assigned_committee),
            "requires_approval": row.requires_approval,
            "triggered_at": row.triggered_at.isoformat() if row.triggered_at else None,
            "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "dismissed_at": row.dismissed_at.isoformat() if row.dismissed_at else None,
            "acknowledged_by": row.acknowledged_by,
            "resolved_by": row.resolved_by,
            "dismissed_by": row.dismissed_by,
            "resolution_notes": row.resolution_notes,
            "dismissal_reason": row.dismissal_reason,
            "alert_metadata": row.alert_metadata,
            "related_metric": row.related_metric,
            "br_id": row.br_id,
            "created_at": row.triggered_at.isoformat() if row.triggered_at else None,  # Use triggered_at as created_at
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        
        # Get period information
        if row.financial_period_id:
            from app.models.financial_period import FinancialPeriod
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == row.financial_period_id
            ).first()
            if period:
                alert_dict["period_year"] = period.period_year
                alert_dict["period_month"] = period.period_month
                alert_dict["period"] = f"{period.period_year}-{str(period.period_month).zfill(2)}"
        
        # Try to get file information from financial_period_id
        if row.financial_period_id and not alert_dict.get("file_name"):
            from app.models.document_upload import DocumentUpload
            # Look for document uploads for this property and period
            uploads = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == row.property_id,
                DocumentUpload.period_id == row.financial_period_id
            ).order_by(DocumentUpload.upload_date.desc()).all()
            
            # Prefer income statement for DSCR alerts, otherwise use most recent
            alert_type_str = alert_dict.get("alert_type", "")
            for upload in uploads:
                if upload.document_type == 'income_statement' or (alert_type_str == 'DSCR_BREACH' and upload.document_type == 'income_statement'):
                    alert_dict["file_name"] = upload.file_name
                    alert_dict["document_type"] = upload.document_type
                    alert_dict["document_id"] = upload.id
                    break
            
            # If no income statement, use most recent document
            if not alert_dict.get("file_name") and uploads:
                alert_dict["file_name"] = uploads[0].file_name
                alert_dict["document_type"] = uploads[0].document_type
                alert_dict["document_id"] = uploads[0].id
        
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

    # Properties at risk (distinct properties with active alerts)
    properties_at_risk_sql = """
        SELECT COUNT(DISTINCT p.id)
        FROM properties p
        LEFT JOIN committee_alerts ca
          ON ca.property_id = p.id AND ca.status = 'ACTIVE'
        LEFT JOIN document_uploads du
          ON du.property_id = p.id
        LEFT JOIN alerts a
          ON a.document_id = du.id AND a.status = 'active'
        WHERE p.status = 'active'
          AND (ca.id IS NOT NULL OR a.id IS NOT NULL)
    """
    properties_at_risk = db.execute(text(properties_at_risk_sql)).scalar() or 0

    # SLA compliance (percent of alerts meeting SLA deadlines)
    from sqlalchemy import func
    now = datetime.utcnow()
    total_sla = db.query(func.count(CommitteeAlert.id)).filter(
        CommitteeAlert.sla_due_at.isnot(None)
    ).scalar() or 0
    compliant_sla = db.query(func.count(CommitteeAlert.id)).filter(
        CommitteeAlert.sla_due_at.isnot(None),
        or_(
            CommitteeAlert.status == AlertStatus.RESOLVED,
            CommitteeAlert.sla_due_at >= now
        )
    ).scalar() or 0
    sla_compliance_rate = (compliant_sla / total_sla * 100) if total_sla else 0.0

    # Count active workflow locks
    from app.models.workflow_lock import WorkflowLock, LockStatus
    try:
        active_locks = db.query(func.count(WorkflowLock.id)).filter(
            WorkflowLock.status == LockStatus.ACTIVE
        ).scalar() or 0
    except Exception as e:
        logger.warning(f"Error counting workflow locks (possibly schema mismatch): {e}")
        active_locks = 0

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
        try:
            count = db.query(CommitteeAlert).filter(
                CommitteeAlert.alert_type == alert_type,
                CommitteeAlert.status == AlertStatus.ACTIVE
            ).count()
            if count > 0:
                alerts_by_type[alert_type.value] = count
        except Exception as e:
            # Skip alert types that don't exist in database enum (e.g., DEBT_YIELD_BREACH)
            logger.debug(f"Skipping alert type {alert_type.value} - not in database enum: {e}")
            continue

    return {
        "success": True,
        "total_critical_alerts": critical_alerts,
        "total_active_alerts": active_alerts,
        "total_active_locks": active_locks,
        "properties_at_risk": properties_at_risk,
        "sla_compliance_rate": sla_compliance_rate,
        "properties_with_good_dscr": good_dscr_count,
        "summary": {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "active_locks": active_locks,
            "properties_at_risk": properties_at_risk,
            "sla_compliance_rate": sla_compliance_rate,
            "properties_with_good_dscr": good_dscr_count,
            "alerts_by_committee": alerts_by_committee,
            "alerts_by_type": alerts_by_type,
        }
    }


@router.get("/exit-strategy/{property_id}")
def get_exit_strategy(
    property_id: int,
    db: Session = Depends(get_db)
):
    """Get exit strategy analysis for a property"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Return placeholder response - can be enhanced with actual exit strategy analysis
    return {
        "success": True,
        "property_id": property_id,
        "property_code": property.property_code,
        "strategies": [],
        "message": "Exit strategy analysis endpoint - implementation pending"
    }


# Phase 10: Enhanced API Endpoints

@router.get("/summary")
def get_alerts_summary(
    property_id: Optional[int] = Query(None),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive alert summary for dashboard
    
    Returns counts by status, severity, type, and trends
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CommitteeAlert).filter(
        CommitteeAlert.triggered_at >= cutoff_date
    )
    
    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)
    
    alerts = query.all()
    
    # Counts by status
    by_status = {}
    for status in AlertStatus:
        count = len([a for a in alerts if a.status == status])
        if count > 0:
            by_status[status.value] = count
    
    # Counts by severity
    by_severity = {}
    for severity in AlertSeverity:
        count = len([a for a in alerts if a.severity == severity])
        if count > 0:
            by_severity[severity.value] = count
    
    # Counts by type
    by_type = {}
    for alert_type in AlertType:
        count = len([a for a in alerts if a.alert_type == alert_type])
        if count > 0:
            by_type[alert_type.value] = count
    
    # Active alerts requiring attention
    active_critical = len([a for a in alerts if a.status == AlertStatus.ACTIVE and a.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]])
    
    return {
        "success": True,
        "period_days": days,
        "total_alerts": len(alerts),
        "active_alerts": len([a for a in alerts if a.status == AlertStatus.ACTIVE]),
        "critical_active": active_critical,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_type": by_type,
        "property_id": property_id
    }


@router.get("/trends")
def get_alert_trends(
    property_id: Optional[int] = Query(None),
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get alert trends over time
    
    Returns daily/weekly counts for trend analysis
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CommitteeAlert).filter(
        CommitteeAlert.triggered_at >= cutoff_date
    )
    
    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)
    
    alerts = query.all()
    
    # Group by date
    daily_counts = defaultdict(int)
    for alert in alerts:
        date_key = alert.triggered_at.date().isoformat() if alert.triggered_at else None
        if date_key:
            daily_counts[date_key] += 1
    
    # Convert to sorted list
    trends = sorted([
        {"date": date, "count": count}
        for date, count in daily_counts.items()
    ], key=lambda x: x["date"])
    
    return {
        "success": True,
        "period_days": days,
        "trends": trends,
        "total_alerts": len(alerts),
        "property_id": property_id
    }


@router.post("/bulk-acknowledge")
def bulk_acknowledge_alerts(
    alert_ids: List[int],
    acknowledged_by: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk acknowledge multiple alerts"""
    alerts = db.query(CommitteeAlert).filter(
        CommitteeAlert.id.in_(alert_ids),
        CommitteeAlert.status == AlertStatus.ACTIVE
    ).all()
    
    if not alerts:
        raise HTTPException(status_code=404, detail="No active alerts found")
    
    acknowledged_count = 0
    for alert in alerts:
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        if notes:
            alert.alert_metadata = alert.alert_metadata or {}
            alert.alert_metadata["bulk_acknowledge_notes"] = notes
        acknowledged_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "acknowledged": acknowledged_count,
        "total_requested": len(alert_ids)
    }


@router.get("/{alert_id}/related")
def get_related_alerts(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alerts related to a specific alert"""
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    correlation_service = AlertCorrelationService(db)
    
    # Get related alerts (same property, period, or correlation group)
    related = db.query(CommitteeAlert).filter(
        CommitteeAlert.id != alert_id,
        CommitteeAlert.property_id == alert.property_id
    )
    
    if alert.financial_period_id:
        related = related.filter(
            CommitteeAlert.financial_period_id == alert.financial_period_id
        )
    
    if alert.correlation_group_id:
        related = related.filter(
            CommitteeAlert.correlation_group_id == alert.correlation_group_id
        )
    
    related_alerts = related.limit(20).all()
    
    return {
        "success": True,
        "alert_id": alert_id,
        "related_alerts": [a.to_dict() for a in related_alerts],
        "total": len(related_alerts)
    }


@router.post("/{alert_id}/escalate")
def escalate_alert(
    alert_id: int,
    reason: str,
    target_committee: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually escalate an alert"""
    alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    escalation_service = AlertEscalationService(db)
    
    target_committee_enum = None
    if target_committee:
        try:
            target_committee_enum = CommitteeType(target_committee)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid committee: {target_committee}")
    
    escalated_alert = escalation_service.escalate_alert_manually(
        alert_id=alert_id,
        reason=reason,
        target_committee=target_committee_enum
    )
    
    return {
        "success": True,
        "alert": escalated_alert.to_dict(),
        "escalation_level": escalated_alert.escalation_level
    }


@router.get("/analytics")
def get_alert_analytics(
    property_id: Optional[int] = Query(None),
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive alert analytics
    
    Returns resolution times, frequency analysis, type distribution, etc.
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CommitteeAlert).filter(
        CommitteeAlert.triggered_at >= cutoff_date
    )
    
    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)
    
    alerts = query.all()
    
    # Resolution time analysis
    resolved_alerts = [a for a in alerts if a.status == AlertStatus.RESOLVED and a.resolved_at and a.triggered_at]
    resolution_times = []
    for alert in resolved_alerts:
        hours = (alert.resolved_at - alert.triggered_at).total_seconds() / 3600
        resolution_times.append(hours)
    
    avg_resolution_hours = sum(resolution_times) / len(resolution_times) if resolution_times else None
    
    # Frequency by type
    type_frequency = {}
    for alert_type in AlertType:
        count = len([a for a in alerts if a.alert_type == alert_type])
        if count > 0:
            type_frequency[alert_type.value] = count
    
    # Property comparison (if no property filter)
    property_counts = {}
    if not property_id:
        for alert in alerts:
            prop_id = alert.property_id
            property_counts[prop_id] = property_counts.get(prop_id, 0) + 1
    
    return {
        "success": True,
        "period_days": days,
        "total_alerts": len(alerts),
        "resolved_count": len(resolved_alerts),
        "average_resolution_hours": avg_resolution_hours,
        "type_frequency": type_frequency,
        "property_distribution": property_counts if not property_id else None,
        "property_id": property_id
    }
