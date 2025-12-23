"""
Risk Workbench API Endpoint

Unifies anomalies, alerts, and review items in a single view.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from sqlalchemy.sql import text
import logging

from app.db.database import get_db
from app.models.anomaly_detection import AnomalyDetection
from app.models.committee_alert import CommitteeAlert, AlertStatus, AlertSeverity
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk-workbench", tags=["risk-workbench"])


@router.get("/unified")
async def get_unified_risk_items(
    property_id: Optional[int] = Query(None),
    document_type: Optional[str] = Query(None),
    anomaly_category: Optional[str] = Query(None),
    sla_breach: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at", description="Column to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Get unified view of anomalies, alerts, and review items.
    
    Returns columns: type, severity, property, age, impact, status, assignee, due_date
    """
    try:
        # Build unified query
        # 1. Anomalies
        anomalies_query = db.query(
            AnomalyDetection.id.label('id'),
            func.cast('anomaly', text).label('type'),
            AnomalyDetection.severity.label('severity'),
            Property.property_code.label('property'),
            func.extract('epoch', func.now() - AnomalyDetection.detected_at).label('age_seconds'),
            AnomalyDetection.impact_amount.label('impact'),
            func.cast(None, text).label('status'),
            func.cast(None, text).label('assignee'),
            func.cast(None, text).label('due_date'),
            AnomalyDetection.detected_at.label('created_at')
        ).join(
            DocumentUpload, AnomalyDetection.document_id == DocumentUpload.id
        ).join(
            Property, DocumentUpload.property_id == Property.id
        )
        
        # 2. Alerts
        alerts_query = db.query(
            CommitteeAlert.id.label('id'),
            func.cast('alert', text).label('type'),
            func.cast(CommitteeAlert.severity, text).label('severity'),
            Property.property_code.label('property'),
            func.extract('epoch', func.now() - CommitteeAlert.created_at).label('age_seconds'),
            CommitteeAlert.business_impact_score.label('impact'),
            func.cast(CommitteeAlert.status, text).label('status'),
            func.cast(None, text).label('assignee'),
            CommitteeAlert.sla_due_at.label('due_date'),
            CommitteeAlert.created_at.label('created_at')
        ).join(
            Property, CommitteeAlert.property_id == Property.id
        )
        
        # Apply filters
        if property_id:
            anomalies_query = anomalies_query.filter(Property.id == property_id)
            alerts_query = alerts_query.filter(Property.id == property_id)
        
        if document_type:
            anomalies_query = anomalies_query.filter(DocumentUpload.document_type == document_type)
        
        if anomaly_category:
            anomalies_query = anomalies_query.filter(AnomalyDetection.anomaly_category == anomaly_category)
        
        if sla_breach is not None:
            if sla_breach:
                alerts_query = alerts_query.filter(
                    and_(
                        CommitteeAlert.sla_due_at.isnot(None),
                        CommitteeAlert.sla_due_at < datetime.utcnow(),
                        CommitteeAlert.status != AlertStatus.RESOLVED
                    )
                )
            else:
                alerts_query = alerts_query.filter(
                    or_(
                        CommitteeAlert.sla_due_at.is_(None),
                        CommitteeAlert.sla_due_at >= datetime.utcnow(),
                        CommitteeAlert.status == AlertStatus.RESOLVED
                    )
                )
        
        # Union queries
        unified_query = anomalies_query.union_all(alerts_query)
        
        # Apply sorting - default to created_at if sort_by is not in the result set
        valid_sort_fields = ['id', 'type', 'severity', 'property', 'age_seconds', 'impact', 'status', 'created_at']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        try:
            if sort_order == "desc":
                unified_query = unified_query.order_by(text(f"{sort_by} DESC"))
            else:
                unified_query = unified_query.order_by(text(f"{sort_by} ASC"))
        except Exception as e:
            logger.warning(f"Invalid sort field {sort_by}, defaulting to created_at: {e}")
            unified_query = unified_query.order_by(text("created_at DESC"))
        
        # Pagination
        try:
            total = db.execute(func.count().select_from(unified_query.subquery())).scalar() or 0
            offset = (page - 1) * page_size
            items = db.execute(unified_query.offset(offset).limit(page_size)).fetchall()
        except Exception as e:
            logger.error(f"Error executing unified query: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Format results
        results = []
        for item in items:
            try:
                results.append({
                    'id': item.id,
                    'type': item.type,
                    'severity': item.severity,
                    'property': item.property,
                    'age_days': round(item.age_seconds / 86400, 1) if item.age_seconds else 0,
                    'impact': float(item.impact) if item.impact else 0.0,
                    'status': item.status,
                    'assignee': item.assignee,
                    'due_date': item.due_date.isoformat() if item.due_date else None,
                    'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None
                })
            except Exception as e:
                logger.warning(f"Error formatting item {item.id}: {e}")
                continue
        
        return {
            'items': results,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if total > 0 else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_unified_risk_items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load unified risk items: {str(e)}")
