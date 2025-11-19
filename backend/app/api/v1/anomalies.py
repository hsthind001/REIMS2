"""
Anomaly Detection API Endpoints
Provides API access to anomaly detection and management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.anomaly_detection_service import AnomalyDetectionService
from pydantic import BaseModel


router = APIRouter()


class AnomalyResponse(BaseModel):
    """Anomaly response schema."""
    type: str
    severity: str
    record_id: Optional[int] = None
    field_name: Optional[str] = None
    value: Optional[float] = None
    message: str
    details: dict


class AnomalyDetectionRequest(BaseModel):
    """Request to trigger anomaly detection."""
    property_id: int
    table_name: str
    lookback_months: int = 12
    method: str = "statistical"  # statistical or ml


@router.get("/", response_model=List[AnomalyResponse])
async def list_anomalies(
    property_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    List detected anomalies with optional filters.
    
    Query Parameters:
    - property_id: Filter by property
    - severity: Filter by severity (critical, high, medium, low)
    - limit: Maximum results (default: 100, max: 1000)
    """
    from sqlalchemy import text
    
    # Build SQL query (models don't exist yet, use direct SQL)
    # Include financial metrics to show underlying calculation data
    sql = """
        SELECT 
            ad.id,
            ad.document_id,
            ad.field_name,
            ad.field_value,
            ad.expected_value,
            ad.anomaly_type,
            ad.severity,
            ad.confidence,
            ad.z_score,
            ad.percentage_change,
            p.property_code,
            p.id as property_id,
            fp.period_year,
            fp.period_month,
            fp.id as period_id,
            du.file_name,
            du.document_type,
            du.upload_date,
            -- Include underlying metrics for calculated fields
            fm.total_current_assets,
            fm.total_current_liabilities,
            fm.total_liabilities,
            fm.total_equity,
            fm.total_assets,
            fm.occupancy_rate,
            fm.total_units,
            fm.occupied_units
        FROM anomaly_detections ad
        JOIN document_uploads du ON ad.document_id = du.id
        JOIN properties p ON du.property_id = p.id
        JOIN financial_periods fp ON du.period_id = fp.id
        LEFT JOIN financial_metrics fm ON fm.property_id = p.id AND fm.period_id = fp.id
        WHERE 1=1
    """
    
    params = {}
    
    if property_id:
        sql += " AND du.property_id = :property_id"
        params['property_id'] = property_id
    
    if severity:
        sql += " AND ad.severity = :severity"
        params['severity'] = severity
    
    sql += " ORDER BY ad.detected_at DESC LIMIT :limit"
    params['limit'] = limit
    
    results = db.execute(text(sql), params).fetchall()
    
    # Build response
    def safe_float(value):
        """Safely convert value to float, handling percentages and strings."""
        if not value:
            return None
        try:
            # Remove percentage sign and convert
            if isinstance(value, str):
                value = value.replace('%', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    return [
        AnomalyResponse(
            type=row.anomaly_type,
            severity=row.severity,
            record_id=row.id,
            field_name=row.field_name,
            value=safe_float(row.field_value),
            message=f"{row.property_code} ({row.period_year}/{row.period_month:02d}): {row.field_name} = {row.field_value} (expected: {row.expected_value or 'normal range'})",
            details={
                'property_code': row.property_code,
                'property_id': row.property_id,
                'period': f"{row.period_year}/{row.period_month:02d}",
                'period_id': row.period_id,
                'document_id': row.document_id,
                'file_name': row.file_name,
                'document_type': row.document_type,
                'upload_date': row.upload_date.isoformat() if row.upload_date else None,
                'expected_value': row.expected_value,
                'field_value': row.field_value,
                'z_score': safe_float(row.z_score),
                'percentage_change': safe_float(row.percentage_change),
                'confidence': safe_float(row.confidence) if row.confidence else None,
                # Include underlying calculation data
                'total_current_assets': safe_float(getattr(row, 'total_current_assets', None)),
                'total_current_liabilities': safe_float(getattr(row, 'total_current_liabilities', None)),
                'total_liabilities': safe_float(getattr(row, 'total_liabilities', None)),
                'total_equity': safe_float(getattr(row, 'total_equity', None)),
                'total_assets': safe_float(getattr(row, 'total_assets', None)),
                'total_units': safe_float(getattr(row, 'total_units', None)),
                'occupied_units': safe_float(getattr(row, 'occupied_units', None)),
            }
        )
        for row in results
    ]


@router.get("/{anomaly_id}")
async def get_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific anomaly."""
    # Would query anomaly_detections table by ID
    return {
        "id": anomaly_id,
        "type": "z_score",
        "severity": "high",
        "message": "Anomaly details"
    }


@router.post("/detect", response_model=List[AnomalyResponse])
async def trigger_anomaly_detection(
    request: AnomalyDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger anomaly detection for a property.
    
    Methods:
    - statistical: Z-score, percentage change, missing data
    - ml: Isolation Forest and LOF
    """
    anomaly_service = AnomalyDetectionService(db)
    
    if request.method == "statistical":
        anomalies = anomaly_service.detect_statistical_anomalies(
            property_id=request.property_id,
            table_name=request.table_name,
            lookback_months=request.lookback_months
        )
    else:  # ml
        anomalies = anomaly_service.detect_ml_anomalies(
            property_id=request.property_id,
            table_name=request.table_name,
            method='iforest'
        )
    
    # Convert to response format
    return [
        AnomalyResponse(
            type=a['type'],
            severity=a['severity'],
            record_id=a.get('record_id'),
            field_name=a.get('field_name'),
            value=a.get('value'),
            message=a['message'],
            details={k: v for k, v in a.items() if k not in ['type', 'severity', 'message']}
        )
        for a in anomalies
    ]


@router.put("/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an anomaly (mark as reviewed)."""
    # Would update anomaly_detections table
    return {
        "id": anomaly_id,
        "acknowledged": True,
        "acknowledged_by": current_user.id,
        "acknowledged_at": datetime.utcnow().isoformat()
    }

