"""
Anomaly Detection API Endpoints
Provides API access to anomaly detection and management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.anomaly_detection_service import AnomalyDetectionService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


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


@router.post("/detect/{upload_id}", response_model=dict)
async def trigger_anomaly_detection(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Manually trigger anomaly detection for an existing document upload.
    
    Useful for:
    - Re-running anomaly detection after threshold changes
    - Running detection on documents uploaded before anomaly detection was implemented
    - Testing anomaly detection logic
    
    Returns:
    - Success status
    - Number of anomalies detected
    """
    from app.models.document_upload import DocumentUpload
    from app.models.financial_period import FinancialPeriod
    from app.services.extraction_orchestrator import ExtractionOrchestrator
    from app.services.anomaly_detector import StatisticalAnomalyDetector
    
    # Verify upload exists
    upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Check if extraction is completed
    if upload.extraction_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot detect anomalies - extraction status is '{upload.extraction_status}'. Must be 'completed'."
        )
    
    try:
        # Get the period for this upload
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.id == upload.period_id
        ).first()
        
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Period not found for upload {upload_id}"
            )
        
        # Delete existing anomalies for this upload (re-detection)
        from sqlalchemy import text
        deleted_count = db.execute(
            text("DELETE FROM anomaly_detections WHERE document_id = :upload_id"),
            {"upload_id": upload_id}
        ).rowcount
        db.commit()
        
        # Run anomaly detection
        orchestrator = ExtractionOrchestrator(db)
        detector = StatisticalAnomalyDetector(db)
        
        if upload.document_type == 'income_statement':
            orchestrator._detect_income_statement_anomalies(upload, period, detector)
        elif upload.document_type == 'balance_sheet':
            orchestrator._detect_balance_sheet_anomalies(upload, period, detector)
        elif upload.document_type == 'cash_flow':
            orchestrator._detect_cash_flow_anomalies(upload, period, detector)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Anomaly detection not supported for document type: {upload.document_type}"
            )
        
        db.commit()
        
        # Count new anomalies
        new_anomaly_count = db.execute(
            text("SELECT COUNT(*) FROM anomaly_detections WHERE document_id = :upload_id"),
            {"upload_id": upload_id}
        ).scalar()
        
        return {
            "success": True,
            "upload_id": upload_id,
            "document_type": upload.document_type,
            "deleted_old_anomalies": deleted_count,
            "new_anomalies_detected": new_anomaly_count,
            "message": f"Anomaly detection completed. {new_anomaly_count} anomalies detected."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


@router.get("/", response_model=List[AnomalyResponse])
async def list_anomalies(
    property_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None, description="Filter by document type (income_statement, balance_sheet, cash_flow, rent_roll)"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    List detected anomalies with optional filters.
    
    Query Parameters:
    - property_id: Filter by property
    - severity: Filter by severity (critical, high, medium, low)
    - document_type: Filter by document type (income_statement, balance_sheet, cash_flow, rent_roll)
    - limit: Maximum results (default: 100, max: 1000)
    """
    from sqlalchemy import text
    
    # Build SQL query (models don't exist yet, use direct SQL)
    # Include financial metrics to show underlying calculation data
    # Include account name from chart_of_accounts
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
            -- Account name from chart_of_accounts
            COALESCE(coa.account_name, ad.field_name) as account_name,
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
        LEFT JOIN chart_of_accounts coa ON coa.account_code = ad.field_name
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
    
    if document_type:
        sql += " AND du.document_type = :document_type"
        params['document_type'] = document_type
    
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
                'period_year': row.period_year,
                'period_month': row.period_month,
                'document_id': row.document_id,
                'file_name': row.file_name,
                'document_type': row.document_type,
                'upload_date': row.upload_date.isoformat() if row.upload_date else None,
                'expected_value': row.expected_value,
                'field_value': row.field_value,
                'account_name': getattr(row, 'account_name', None) or row.field_name,
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


class FieldCoordinatesResponse(BaseModel):
    """Response for field coordinates endpoint."""
    has_coordinates: bool
    coordinates: Optional[dict] = None
    pdf_url: Optional[str] = None
    explanation: str


@router.get("/{anomaly_id}/field-coordinates", response_model=FieldCoordinatesResponse)
async def get_field_coordinates(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get field coordinates and PDF URL for an anomaly.
    
    Returns:
    - has_coordinates: Whether coordinates exist in database
    - coordinates: Field coordinates (x0, y0, x1, y1, page_number) if available
    - pdf_url: Presigned URL for PDF document
    - explanation: Explanation message for user
    """
    from sqlalchemy import text, and_
    from app.models.document_upload import DocumentUpload
    from app.models.property import Property
    from app.models.financial_period import FinancialPeriod
    from app.models.balance_sheet_data import BalanceSheetData
    from app.models.income_statement_data import IncomeStatementData
    from app.models.cash_flow_data import CashFlowData
    from app.models.rent_roll_data import RentRollData
    from app.db.minio_client import get_file_url
    from app.core.config import settings
    
    # Get anomaly details
    anomaly_query = text("""
        SELECT 
            ad.id,
            ad.document_id,
            ad.field_name,
            du.file_name,
            du.document_type,
            du.file_path,
            du.property_id,
            du.period_id,
            p.property_code,
            fp.period_year,
            fp.period_month
        FROM anomaly_detections ad
        JOIN document_uploads du ON ad.document_id = du.id
        JOIN properties p ON du.property_id = p.id
        JOIN financial_periods fp ON du.period_id = fp.id
        WHERE ad.id = :anomaly_id
    """)
    
    result = db.execute(anomaly_query, {"anomaly_id": anomaly_id}).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found"
        )
    
    document_id = result.document_id
    field_name = result.field_name  # This is the account_code
    document_type = result.document_type
    file_path = result.file_path
    property_code = result.property_code
    period_year = result.period_year
    period_month = result.period_month
    
    # Query financial data tables for coordinates
    coordinates = None
    has_coordinates = False
    
    # Try each table based on document type
    if document_type == 'balance_sheet':
        record = db.query(BalanceSheetData).filter(
            and_(
                BalanceSheetData.upload_id == document_id,
                BalanceSheetData.account_code == field_name
            )
        ).first()
        
        if record and record.extraction_x0 is not None:
            coordinates = {
                "x0": float(record.extraction_x0),
                "y0": float(record.extraction_y0),
                "x1": float(record.extraction_x1),
                "y1": float(record.extraction_y1),
                "page_number": record.page_number or 1
            }
            has_coordinates = True
    
    elif document_type == 'income_statement':
        record = db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.upload_id == document_id,
                IncomeStatementData.account_code == field_name
            )
        ).first()
        
        if record and record.extraction_x0 is not None:
            coordinates = {
                "x0": float(record.extraction_x0),
                "y0": float(record.extraction_y0),
                "x1": float(record.extraction_x1),
                "y1": float(record.extraction_y1),
                "page_number": record.page_number or 1
            }
            has_coordinates = True
    
    elif document_type == 'cash_flow':
        record = db.query(CashFlowData).filter(
            and_(
                CashFlowData.upload_id == document_id,
                CashFlowData.account_code == field_name
            )
        ).first()
        
        if record and record.extraction_x0 is not None:
            coordinates = {
                "x0": float(record.extraction_x0),
                "y0": float(record.extraction_y0),
                "x1": float(record.extraction_x1),
                "y1": float(record.extraction_y1),
                "page_number": record.page_number or 1
            }
            has_coordinates = True
    
    elif document_type == 'rent_roll':
        # For rent_roll, field_name might be a field name (monthly_rent, annual_rent, etc.)
        # We need to find any record with coordinates for this document
        # Since rent_roll anomalies are typically aggregate metrics, coordinates may not be available
        # Try to find a record with coordinates (any record from this document)
        record = db.query(RentRollData).filter(
            and_(
                RentRollData.upload_id == document_id,
                RentRollData.extraction_x0.isnot(None)
            )
        ).first()
        
        if record and record.extraction_x0 is not None:
            coordinates = {
                "x0": float(record.extraction_x0),
                "y0": float(record.extraction_y0),
                "x1": float(record.extraction_x1),
                "y1": float(record.extraction_y1),
                "page_number": record.page_number or 1
            }
            has_coordinates = True
    
    # Get PDF URL
    pdf_url = None
    if file_path:
        try:
            pdf_url = get_file_url(
                object_name=file_path,
                bucket_name=settings.MINIO_BUCKET_NAME,
                expires_seconds=3600  # 1 hour
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF URL: {e}")
    
    # Generate explanation
    if has_coordinates:
        explanation = f"This value was extracted from the {document_type.replace('_', ' ')} document at the location shown in the PDF."
    else:
        explanation = f"This is a calculated metric derived from multiple line items in the {document_type.replace('_', ' ')}. The specific field location is not available because it is computed from other values in the document."
    
    return FieldCoordinatesResponse(
        has_coordinates=has_coordinates,
        coordinates=coordinates,
        pdf_url=pdf_url,
        explanation=explanation
    )

