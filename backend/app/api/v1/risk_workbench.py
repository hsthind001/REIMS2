"""
Risk Workbench API Endpoint

Unifies anomalies, alerts, and review items in a single view.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import re
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, String
from sqlalchemy.sql import text
import logging

from app.db.database import get_db
from app.models.anomaly_detection import AnomalyDetection
from app.models.committee_alert import CommitteeAlert, AlertStatus, AlertSeverity
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk-workbench", tags=["risk-workbench"])


def _parse_metadata(raw_metadata: Optional[str]) -> Dict[str, Any]:
    if not raw_metadata:
        return {}
    if isinstance(raw_metadata, dict):
        return raw_metadata
    if isinstance(raw_metadata, str):
        try:
            return json.loads(raw_metadata)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    return {}


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        if cleaned in {"", "-", "N/A", "NA", "n/a", "na"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _humanize_account_name(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value or not isinstance(raw_value, str):
        return None
    if not any(char.isalpha() for char in raw_value):
        return None
    cleaned = raw_value.replace("_", " ").replace("-", " ").strip()
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    return cleaned.title()


def _extract_alert_title_name(raw_title: Optional[str]) -> Optional[str]:
    if not raw_title or not isinstance(raw_title, str):
        return None
    if ":" in raw_title:
        candidate = raw_title.split(":", 1)[1].strip()
        return candidate or None
    return raw_title.strip() or None


def _extract_numeric_from_text(raw_text: Optional[str]) -> Optional[float]:
    if not raw_text or not isinstance(raw_text, str):
        return None
    match = re.search(r"Value:\s*\$?([\-0-9,\.]+)", raw_text, flags=re.IGNORECASE)
    if not match:
        return None
    return _safe_float(match.group(1))


@router.get("/unified")
async def get_unified_risk_items(
    property_id: Optional[int] = Query(None),
    document_type: Optional[str] = Query(None),
    period: Optional[str] = Query(None, description="Filter by period in YYYY-MM format"),
    anomaly_category: Optional[str] = Query(None),
    sla_breach: Optional[bool] = Query(None),
    item_type: Optional[str] = Query(None, description="Filter by item type: anomaly or alert"),
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
        period_year = None
        period_month = None
        if period:
            try:
                year_str, month_str = period.split("-", 1)
                period_year = int(year_str)
                period_month = int(month_str)
                if period_month < 1 or period_month > 12:
                    raise ValueError("Month out of range")
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid period format. Use YYYY-MM, e.g. 2025-10."
                )

        # Build unified query
        # 1. Anomalies
        anomalies_query = db.query(
            AnomalyDetection.id.label('id'),
            func.cast('anomaly', String()).label('type'),
            AnomalyDetection.severity.label('severity'),
            Property.property_code.label('property'),
            func.extract('epoch', func.now() - AnomalyDetection.detected_at).label('age_seconds'),
            AnomalyDetection.impact_amount.label('impact'),
            func.cast(None, String()).label('status'),
            func.cast(None, String()).label('assignee'),
            func.cast(None, String()).label('due_date'),
            AnomalyDetection.detected_at.label('created_at'),
            ChartOfAccounts.account_name.label('account_name'),
            AnomalyDetection.field_name.label('field_name'),
            AnomalyDetection.field_value.label('field_value'),
            AnomalyDetection.expected_value.label('expected_value'),
            func.cast(AnomalyDetection.metadata_json, String()).label('metadata_json'),
            func.cast(None, String()).label('alert_title'),
            func.cast(None, String()).label('alert_description')
        ).join(
            DocumentUpload, AnomalyDetection.document_id == DocumentUpload.id
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).outerjoin(
            ChartOfAccounts, ChartOfAccounts.account_code == AnomalyDetection.field_name
        )
        
        # 2. Alerts
        alerts_query = db.query(
            CommitteeAlert.id.label('id'),
            func.cast('alert', String()).label('type'),
            func.cast(CommitteeAlert.severity, String()).label('severity'),
            Property.property_code.label('property'),
            func.extract('epoch', func.now() - CommitteeAlert.created_at).label('age_seconds'),
            CommitteeAlert.business_impact_score.label('impact'),
            func.cast(CommitteeAlert.status, String()).label('status'),
            func.cast(None, String()).label('assignee'),
            func.cast(CommitteeAlert.sla_due_at, String()).label('due_date'),
            CommitteeAlert.created_at.label('created_at'),
            func.cast(None, String()).label('account_name'),
            CommitteeAlert.related_metric.label('field_name'),
            func.cast(CommitteeAlert.actual_value, String()).label('field_value'),
            func.cast(CommitteeAlert.threshold_value, String()).label('expected_value'),
            func.cast(CommitteeAlert.alert_metadata, String()).label('metadata_json'),
            CommitteeAlert.title.label('alert_title'),
            CommitteeAlert.description.label('alert_description')
        ).join(
            Property, CommitteeAlert.property_id == Property.id
        )
        
        # Apply filters
        if property_id:
            anomalies_query = anomalies_query.filter(Property.id == property_id)
            alerts_query = alerts_query.filter(Property.id == property_id)
        
        if document_type:
            anomalies_query = anomalies_query.filter(DocumentUpload.document_type == document_type)

        if period_year and period_month:
            anomalies_query = anomalies_query.join(
                FinancialPeriod,
                FinancialPeriod.id == DocumentUpload.period_id
            ).filter(
                FinancialPeriod.period_year == period_year,
                FinancialPeriod.period_month == period_month
            )

        if anomaly_category:
            anomalies_query = anomalies_query.filter(AnomalyDetection.anomaly_category == anomaly_category)

        if period_year and period_month:
            alerts_query = alerts_query.filter(
                func.extract('year', CommitteeAlert.created_at) == period_year,
                func.extract('month', CommitteeAlert.created_at) == period_month
            )

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
        normalized_type = item_type.lower() if item_type else None
        if normalized_type == "anomaly":
            unified_query = anomalies_query
        elif normalized_type == "alert":
            unified_query = alerts_query
        else:
            unified_query = anomalies_query.union_all(alerts_query)
        
        # Create subquery for ordering and pagination
        # Apply sorting - default to created_at if sort_by is not in the result set
        valid_sort_fields = ['id', 'type', 'severity', 'property', 'age_seconds', 'impact', 'status', 'created_at', 'account_name']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        # Create subquery from union
        subquery = unified_query.subquery()
        
        # Pagination
        offset = (page - 1) * page_size
        try:
            # Count total
            count_query = db.query(func.count()).select_from(subquery)
            total = count_query.scalar() or 0
            
            # Get paginated results with ordering
            # Use text() for dynamic column ordering on subquery
            if sort_order == "desc":
                order_sql = f"{sort_by} DESC"
            else:
                order_sql = f"{sort_by} ASC"
            
            # Query subquery with ordering
            items_query = db.query(subquery).order_by(text(order_sql)).offset(offset).limit(page_size)
            items = items_query.all()
        except Exception as e:
            logger.warning(f"Error with sort field {sort_by}, trying default: {e}")
            # Fallback to default sorting
            try:
                items_query = db.query(subquery).order_by(text("created_at DESC")).offset(offset).limit(page_size)
                items = items_query.all()
            except Exception as e2:
                logger.error(f"Error executing unified query even with fallback: {e2}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Database error: {str(e2)}")
        
        # Format results
        results = []
        for item in items:
            try:
                metadata = _parse_metadata(item.metadata_json) if item.type == 'anomaly' else {}
                impact_value = item.impact
                actual_value = _safe_float(metadata.get("actual_value")) or _safe_float(item.field_value)
                expected_value = _safe_float(metadata.get("expected_value")) or _safe_float(item.expected_value)
                if item.type == 'anomaly' and impact_value is None:
                    if actual_value is not None and expected_value is not None:
                        impact_value = abs(actual_value - expected_value)
                if item.type == 'alert' and impact_value is None:
                    if actual_value is not None and expected_value is not None:
                        impact_value = abs(actual_value - expected_value)
                    elif actual_value is not None:
                        impact_value = actual_value
                    elif item.alert_description:
                        impact_value = _extract_numeric_from_text(item.alert_description)

                account_code = None
                account_name = None
                field_name = None
                if item.type == 'anomaly':
                    field_name = item.field_name
                    account_code = metadata.get("account_code") or metadata.get("field_name") or field_name
                    account_name = (
                        metadata.get("account_name")
                        or metadata.get("account_description")
                        or item.account_name
                        or _humanize_account_name(account_code)
                    )
                elif item.type == 'alert':
                    field_name = item.field_name
                    account_code = metadata.get("account_code") or field_name
                    account_name = (
                        metadata.get("account_name")
                        or metadata.get("account_description")
                        or _extract_alert_title_name(item.alert_title)
                        or _humanize_account_name(account_code)
                    )

                results.append({
                    'id': item.id,
                    'type': item.type,
                    'severity': item.severity,
                    'property': item.property,
                    'age_days': round(item.age_seconds / 86400, 1) if item.age_seconds else 0,
                    'impact': float(impact_value) if impact_value is not None else None,
                    'status': item.status,
                    'assignee': item.assignee,
                    'due_date': item.due_date.isoformat() if item.due_date else None,
                    'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
                    'account_code': account_code,
                    'account_name': account_name,
                    'field_name': field_name
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
