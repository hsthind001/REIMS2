"""
Alert Monitoring Tasks
Celery tasks for periodic alert monitoring and escalation
"""
from celery import shared_task
from sqlalchemy.orm import Session
from typing import Dict, List
import logging

from app.db.database import SessionLocal
from app.services.alert_trigger_service import AlertTriggerService
from app.services.alert_escalation_service import AlertEscalationService
from app.services.alert_prioritization_service import AlertPrioritizationService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.committee_alert import CommitteeAlert, AlertStatus

logger = logging.getLogger(__name__)


@shared_task(name="evaluate_alerts_for_property")
def evaluate_alerts_for_property(property_id: int, period_id: int = None):
    """
    Evaluate alerts for a specific property/period
    
    Args:
        property_id: Property ID
        period_id: Optional period ID (if None, evaluates all periods)
    
    Returns:
        Summary of evaluation results
    """
    db = SessionLocal()
    try:
        trigger_service = AlertTriggerService(db)
        
        if period_id:
            result = trigger_service.evaluate_and_trigger_alerts(
                property_id=property_id,
                period_id=period_id
            )
            return {
                "success": True,
                "property_id": property_id,
                "period_id": period_id,
                "alerts_triggered": len(result)
            }
        else:
            result = trigger_service.evaluate_property_alerts(
                property_id=property_id
            )
            return {
                "success": True,
                "property_id": property_id,
                **result
            }
    except Exception as e:
        logger.error(f"Error evaluating alerts for property {property_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="escalate_overdue_alerts")
def escalate_overdue_alerts():
    """
    Check and escalate overdue alerts
    
    Runs periodically to escalate alerts that haven't been acknowledged
    within their time thresholds.
    
    Returns:
        Summary of escalation actions
    """
    db = SessionLocal()
    try:
        escalation_service = AlertEscalationService(db)
        result = escalation_service.check_and_escalate_alerts()
        
        logger.info(
            f"Escalation check completed: {result['escalated']} alerts escalated "
            f"out of {result['total_checked']} checked"
        )
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error escalating alerts: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="update_alert_priorities")
def update_alert_priorities():
    """
    Update priority scores for all active alerts
    
    Recalculates priority scores based on current conditions.
    Should run periodically to keep priorities up-to-date.
    
    Returns:
        Summary of updates
    """
    db = SessionLocal()
    try:
        prioritization_service = AlertPrioritizationService(db)
        
        active_alerts = db.query(CommitteeAlert).filter(
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).all()
        
        updated_count = 0
        for alert in active_alerts:
            try:
                prioritization_service.update_alert_priority(alert)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating priority for alert {alert.id}: {str(e)}")
                continue
        
        db.commit()
        
        logger.info(f"Updated priorities for {updated_count} alerts")
        
        return {
            "success": True,
            "total_alerts": len(active_alerts),
            "updated": updated_count
        }
    except Exception as e:
        logger.error(f"Error updating alert priorities: {str(e)}", exc_info=True)
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="generate_alert_digest")
def generate_alert_digest(property_id: int = None):
    """
    Generate alert digest for properties
    
    Creates a summary of active alerts for email/notification.
    
    Args:
        property_id: Optional property ID (if None, generates for all properties)
    
    Returns:
        Alert digest data
    """
    db = SessionLocal()
    try:
        query = db.query(CommitteeAlert).filter(
            CommitteeAlert.status == AlertStatus.ACTIVE
        )
        
        if property_id:
            query = query.filter(CommitteeAlert.property_id == property_id)
        
        alerts = query.order_by(CommitteeAlert.priority_score.desc()).limit(50).all()
        
        # Group by severity
        by_severity = {}
        for alert in alerts:
            severity = alert.severity.value if alert.severity else "UNKNOWN"
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append({
                "id": alert.id,
                "title": alert.title,
                "property_id": alert.property_id,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
            })
        
        return {
            "success": True,
            "total_alerts": len(alerts),
            "by_severity": by_severity,
            "alerts": [
                {
                    "id": a.id,
                    "title": a.title,
                    "severity": a.severity.value if a.severity else None,
                    "property_id": a.property_id,
                    "priority_score": float(a.priority_score) if a.priority_score else None
                }
                for a in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Error generating alert digest: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="cleanup_resolved_alerts")
def cleanup_resolved_alerts(days_old: int = 90):
    """
    Cleanup old resolved alerts
    
    Archives or removes alerts that have been resolved for a specified number of days.
    
    Args:
        days_old: Number of days since resolution to cleanup
    
    Returns:
        Summary of cleanup actions
    """
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        old_resolved = db.query(CommitteeAlert).filter(
            and_(
                CommitteeAlert.status == AlertStatus.RESOLVED,
                CommitteeAlert.resolved_at < cutoff_date
            )
        ).all()
        
        # For now, just log - actual cleanup/archiving can be implemented later
        logger.info(f"Found {len(old_resolved)} resolved alerts older than {days_old} days")
        
        return {
            "success": True,
            "alerts_found": len(old_resolved),
            "cutoff_date": cutoff_date.isoformat()
        }
    except Exception as e:
        logger.error(f"Error cleaning up resolved alerts: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="monitor_all_properties")
def monitor_all_properties():
    """
    Monitor all properties for alert evaluation
    
    Runs periodic evaluation for all properties with recent financial data.
    Should be scheduled to run daily.
    
    Returns:
        Summary of monitoring results
    """
    db = SessionLocal()
    try:
        # Get all properties
        properties = db.query(Property).all()
        
        trigger_service = AlertTriggerService(db)
        
        results = []
        for property_obj in properties:
            try:
                # Get most recent period
                recent_period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property_obj.id
                ).order_by(FinancialPeriod.period_end_date.desc()).first()
                
                if not recent_period:
                    continue
                
                # Evaluate alerts
                alerts = trigger_service.evaluate_and_trigger_alerts(
                    property_id=property_obj.id,
                    period_id=recent_period.id
                )
                
                results.append({
                    "property_id": property_obj.id,
                    "period_id": recent_period.id,
                    "alerts_triggered": len(alerts)
                })
            except Exception as e:
                logger.error(
                    f"Error monitoring property {property_obj.id}: {str(e)}",
                    exc_info=True
                )
                continue
        
        total_alerts = sum(r["alerts_triggered"] for r in results)
        
        logger.info(
            f"Property monitoring completed: {total_alerts} alerts triggered "
            f"across {len(results)} properties"
        )
        
        return {
            "success": True,
            "properties_monitored": len(results),
            "total_alerts_triggered": total_alerts,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error monitoring properties: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()

