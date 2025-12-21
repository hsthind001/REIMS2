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
from app.services.xai_explanation_service import XAIExplanationService
from app.services.active_learning_service import ActiveLearningService
from app.services.cross_property_intelligence import CrossPropertyIntelligenceService
from app.models.anomaly_explanation import AnomalyExplanation
from app.models.anomaly_detection import AnomalyDetection
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
    anomaly = db.query(AnomalyDetection).filter(
        AnomalyDetection.id == anomaly_id
    ).first()
    
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found"
        )
    
    return {
        "id": anomaly.id,
        "type": anomaly.anomaly_type,
        "severity": anomaly.severity,
        "message": anomaly.message or f"Anomaly detected in {anomaly.account_code}",
        "property_id": anomaly.property_id,
        "account_code": anomaly.account_code,
        "actual_value": float(anomaly.actual_value) if anomaly.actual_value else None,
        "expected_value": float(anomaly.expected_value) if anomaly.expected_value else None,
        "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None
    }


@router.post("/{anomaly_id}/explain")
async def generate_explanation(
    anomaly_id: int,
    method: str = Query("auto", description="Explanation method: 'shap', 'lime', 'auto', or 'root_cause'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate XAI explanation for an anomaly.
    
    Provides:
    - Root cause analysis
    - SHAP feature importance (if enabled)
    - LIME local explanation (if enabled)
    - Natural language explanation
    - Actionable recommendations
    """
    xai_service = XAIExplanationService(db)
    
    # Check if explanation already exists
    existing = xai_service.get_explanation(anomaly_id)
    if existing:
        return {
            "id": existing.id,
            "anomaly_id": anomaly_id,
            "root_cause_type": existing.root_cause_type,
            "root_cause_description": existing.root_cause_description,
            "contributing_factors": existing.contributing_factors,
            "shap_values": existing.shap_values,
            "shap_base_value": float(existing.shap_base_value) if existing.shap_base_value else None,
            "shap_feature_importance": existing.shap_feature_importance,
            "lime_explanation": existing.lime_explanation,
            "lime_intercept": float(existing.lime_intercept) if existing.lime_intercept else None,
            "lime_score": float(existing.lime_score) if existing.lime_score else None,
            "suggested_actions": existing.suggested_actions,
            "action_category": existing.action_category,
            "explanation_generated_at": existing.explanation_generated_at.isoformat() if existing.explanation_generated_at else None,
            "computation_time_ms": existing.computation_time_ms
        }
    
    # Generate new explanation
    try:
        explanation = xai_service.generate_explanation(
            anomaly_id=anomaly_id,
            method=method
        )
        
        return {
            "id": explanation.id,
            "anomaly_id": anomaly_id,
            "root_cause_type": explanation.root_cause_type,
            "root_cause_description": explanation.root_cause_description,
            "contributing_factors": explanation.contributing_factors,
            "shap_values": explanation.shap_values,
            "shap_base_value": float(explanation.shap_base_value) if explanation.shap_base_value else None,
            "shap_feature_importance": explanation.shap_feature_importance,
            "lime_explanation": explanation.lime_explanation,
            "lime_intercept": float(explanation.lime_intercept) if explanation.lime_intercept else None,
            "lime_score": float(explanation.lime_score) if explanation.lime_score else None,
            "suggested_actions": explanation.suggested_actions,
            "action_category": explanation.action_category,
            "explanation_generated_at": explanation.explanation_generated_at.isoformat() if explanation.explanation_generated_at else None,
            "computation_time_ms": explanation.computation_time_ms
        }
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}"
        )


@router.get("/{anomaly_id}/explanation")
async def get_explanation(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get existing XAI explanation for an anomaly."""
    xai_service = XAIExplanationService(db)
    
    explanation = xai_service.get_explanation(anomaly_id)
    
    if not explanation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No explanation found for anomaly {anomaly_id}. Generate one using POST /{anomaly_id}/explain"
        )
    
    return {
        "id": explanation.id,
        "anomaly_id": anomaly_id,
        "root_cause_type": explanation.root_cause_type,
        "root_cause_description": explanation.root_cause_description,
        "contributing_factors": explanation.contributing_factors,
        "shap_values": explanation.shap_values,
        "shap_base_value": float(explanation.shap_base_value) if explanation.shap_base_value else None,
        "shap_feature_importance": explanation.shap_feature_importance,
        "lime_explanation": explanation.lime_explanation,
        "lime_intercept": float(explanation.lime_intercept) if explanation.lime_intercept else None,
        "lime_score": float(explanation.lime_score) if explanation.lime_score else None,
        "suggested_actions": explanation.suggested_actions,
        "action_category": explanation.action_category,
        "explanation_generated_at": explanation.explanation_generated_at.isoformat() if explanation.explanation_generated_at else None,
        "computation_time_ms": explanation.computation_time_ms
    }


@router.get("/property/{property_id}/explanations")
async def get_property_explanations(
    property_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all XAI explanations for anomalies in a property."""
    xai_service = XAIExplanationService(db)
    
    explanations = xai_service.get_explanations_for_property(
        property_id=property_id,
        limit=limit
    )
    
    return [
        {
            "id": exp.id,
            "anomaly_id": exp.anomaly_detection_id,
            "root_cause_type": exp.root_cause_type,
            "root_cause_description": exp.root_cause_description,
            "action_category": exp.action_category,
            "explanation_generated_at": exp.explanation_generated_at.isoformat() if exp.explanation_generated_at else None
        }
        for exp in explanations
    ]


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


@router.post("/{anomaly_id}/feedback")
async def submit_feedback(
    anomaly_id: int,
    feedback_type: str = Query(..., description="Feedback type: 'true_positive', 'false_positive', 'needs_review'"),
    feedback_notes: Optional[str] = Query(None, description="Optional feedback notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback on an anomaly detection.
    
    Used for active learning to improve detection accuracy over time.
    """
    active_learning = ActiveLearningService(db)
    
    try:
        feedback = active_learning.record_feedback(
            anomaly_id=anomaly_id,
            user_id=current_user.id,
            feedback_type=feedback_type,
            feedback_notes=feedback_notes
        )
        
        return {
            "success": True,
            "feedback_id": feedback.id,
            "anomaly_id": anomaly_id,
            "feedback_type": feedback_type,
            "message": "Feedback recorded successfully. This will help improve anomaly detection accuracy."
        }
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get("/property/{property_id}/benchmarks/{account_code}")
async def get_property_benchmark(
    property_id: int,
    account_code: str,
    metric_type: str = Query("balance_sheet", description="Metric type: 'balance_sheet' or 'income_statement'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get property ranking compared to portfolio benchmarks."""
    cross_prop_service = CrossPropertyIntelligenceService(db)
    
    ranking = cross_prop_service.get_property_ranking(
        property_id=property_id,
        account_code=account_code,
        metric_type=metric_type
    )
    
    if not ranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No benchmark data available for {account_code}"
        )
    
    return ranking


@router.get("/property/{property_id}/feedback-stats")
async def get_feedback_statistics(
    property_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get feedback statistics for a property."""
    active_learning = ActiveLearningService(db)
    
    stats = active_learning.get_feedback_statistics(
        property_id=property_id,
        days=days
    )
    
    return stats


@router.get("/property/{property_id}/learned-patterns")
async def get_learned_patterns(
    property_id: int,
    active_only: bool = Query(True, description="Only return active patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get learned patterns for a property."""
    active_learning = ActiveLearningService(db)
    
    patterns = active_learning.get_learned_patterns(
        property_id=property_id,
        active_only=active_only
    )
    
    return [
        {
            "id": p.id,
            "account_code": p.account_code,
            "anomaly_type": p.anomaly_type,
            "pattern_type": p.pattern_type,
            "confidence": float(p.confidence) if p.confidence else None,
            "occurrence_count": p.occurrence_count,
            "auto_suppress": p.auto_suppress,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in patterns
    ]



@router.post("/{anomaly_id}/feedback")
async def submit_feedback(
    anomaly_id: int,
    feedback_type: str = Query(..., description="Feedback type: 'true_positive', 'false_positive', 'needs_review'"),
    feedback_notes: Optional[str] = Query(None, description="Optional feedback notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback on an anomaly detection.
    
    Used for active learning to improve detection accuracy over time.
    """
    active_learning = ActiveLearningService(db)
    
    try:
        feedback = active_learning.record_feedback(
            anomaly_id=anomaly_id,
            user_id=current_user.id,
            feedback_type=feedback_type,
            feedback_notes=feedback_notes
        )
        
        return {
            "success": True,
            "feedback_id": feedback.id,
            "anomaly_id": anomaly_id,
            "feedback_type": feedback_type,
            "message": "Feedback recorded successfully. This will help improve anomaly detection accuracy."
        }
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get("/property/{property_id}/benchmarks/{account_code}")
async def get_property_benchmark(
    property_id: int,
    account_code: str,
    metric_type: str = Query("balance_sheet", description="Metric type: 'balance_sheet' or 'income_statement'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get property ranking compared to portfolio benchmarks."""
    cross_prop_service = CrossPropertyIntelligenceService(db)
    
    ranking = cross_prop_service.get_property_ranking(
        property_id=property_id,
        account_code=account_code,
        metric_type=metric_type
    )
    
    if not ranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No benchmark data available for {account_code}"
        )
    
    return ranking


@router.get("/property/{property_id}/feedback-stats")
async def get_feedback_statistics(
    property_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get feedback statistics for a property."""
    active_learning = ActiveLearningService(db)
    
    stats = active_learning.get_feedback_statistics(
        property_id=property_id,
        days=days
    )
    
    return stats


@router.get("/property/{property_id}/learned-patterns")
async def get_learned_patterns(
    property_id: int,
    active_only: bool = Query(True, description="Only return active patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get learned patterns for a property."""
    active_learning = ActiveLearningService(db)
    
    patterns = active_learning.get_learned_patterns(
        property_id=property_id,
        active_only=active_only
    )
    
    return [
        {
            "id": p.id,
            "account_code": p.account_code,
            "anomaly_type": p.anomaly_type,
            "pattern_type": p.pattern_type,
            "confidence": float(p.confidence) if p.confidence else None,
            "occurrence_count": p.occurrence_count,
            "auto_suppress": p.auto_suppress,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in patterns
    ]
