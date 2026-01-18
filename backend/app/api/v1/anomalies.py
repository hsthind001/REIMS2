"""
Anomaly Detection API Endpoints
Provides API access to anomaly detection and management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json

from app.models.organization import Organization
from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.xai_explanation_service import XAIExplanationService
from app.services.active_learning_service import ActiveLearningService
from app.services.cross_property_intelligence import CrossPropertyIntelligenceService
from app.services.anomaly_export_service import AnomalyExportService
from fastapi import Response, BackgroundTasks
from datetime import date
from app.models.property import Property
from app.models.anomaly_explanation import AnomalyExplanation
from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.models.chart_of_accounts import ChartOfAccounts
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


router = APIRouter()


def _parse_metadata(raw_metadata):
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


def _safe_float(value):
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


@router.post("/detect/all", response_model=dict)
async def trigger_all_anomaly_detection(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Trigger anomaly detection for ALL completed documents in the current organization.
    Runs in the background.
    """
    from app.models.document_upload import DocumentUpload
    from app.services.extraction_orchestrator import ExtractionOrchestrator
    
    # Get all completed uploads for this org
    uploads = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).filter(
        Property.organization_id == current_org.id,
        DocumentUpload.extraction_status == 'completed'
    ).all()
    
    if not uploads:
        return {
            "success": True,
            "message": "No completed documents found."
        }
        
    # Define background task function
    def run_bulk_detection(upload_ids: List[int], org_id: int):
        # Create new session for background task
        from app.db.database import SessionLocal
        db_bg = SessionLocal()
        try:
            orchestrator = ExtractionOrchestrator(db_bg)
            success_count = 0
            
            for upload_id in upload_ids:
                try:
                    upload = db_bg.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
                    if not upload:
                        continue
                        
                    # Re-detect
                    orchestrator._detect_anomalies_for_document(upload)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed bulk detection for doc {upload_id}: {e}")
                    continue
            
            logger.info(f"Bulk anomaly detection completed. Success: {success_count}/{len(upload_ids)}")
            
        except Exception as e:
            logger.error(f"Bulk detection task failed: {e}")
        finally:
            db_bg.close()

    # Queue the task
    upload_ids = [u.id for u in uploads]
    background_tasks.add_task(run_bulk_detection, upload_ids, current_org.id)
    
    return {
        "success": True,
        "message": f"Queued {len(uploads)} documents for anomaly detection.",
        "document_count": len(uploads)
    }


@router.post("/detect/{upload_id}", response_model=dict)
async def trigger_anomaly_detection(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Manually trigger anomaly detection for an existing document upload.
    Restricted to documents owned by the current organization.
    
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
    
    # Check tenancy
    from app.models.property import Property
    upload_property = db.query(Property).filter(Property.id == upload.property_id).first()
    if not upload_property or upload_property.organization_id != current_org.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # 404 to hide existence
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
        elif upload.document_type == 'rent_roll':
            orchestrator._detect_rent_roll_anomalies(upload, period, detector)
        elif upload.document_type == 'mortgage_statement':
            orchestrator._detect_mortgage_statement_anomalies(upload, period, detector)
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
    year: Optional[int] = Query(None, description="Filter by period year (e.g., 2023)"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    List detected anomalies with optional filters.
    Scoped to current organization.
    
    Query Parameters:
    - property_id: Filter by property
    - severity: Filter by severity (critical, high, medium, low)
    - document_type: Filter by document type (income_statement, balance_sheet, cash_flow, rent_roll)
    - year: Filter by period year (e.g., 2023)
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
        AND p.organization_id = :org_id
    """
    
    params = {'org_id': current_org.id}
    
    if property_id:
        sql += " AND du.property_id = :property_id"
        params['property_id'] = property_id
    
    if severity:
        sql += " AND ad.severity = :severity"
        params['severity'] = severity
    
    if document_type:
        sql += " AND du.document_type = :document_type"
        params['document_type'] = document_type
    
    if year:
        sql += " AND fp.period_year = :year"
        params['year'] = year
    
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
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get detailed information about a specific anomaly."""
    from sqlalchemy.orm import load_only
    from app.models.document_upload import DocumentUpload
    
    anomaly = db.query(AnomalyDetection).options(
        load_only(
            AnomalyDetection.id,
            AnomalyDetection.document_id,
            AnomalyDetection.field_name,
            AnomalyDetection.field_value,
            AnomalyDetection.expected_value,
            AnomalyDetection.anomaly_type,
            AnomalyDetection.severity,
            AnomalyDetection.confidence,
            AnomalyDetection.detected_at,
            AnomalyDetection.metadata_json
        )
    ).filter(
        AnomalyDetection.id == anomaly_id
    ).first()
    
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found"
        )

    metadata = _parse_metadata(anomaly.metadata_json)
    property_id = metadata.get("property_id")
    if isinstance(property_id, str) and property_id.isdigit():
        property_id = int(property_id)
    if property_id is None and anomaly.document_id:
        property_id = db.query(DocumentUpload.property_id).filter(
            DocumentUpload.id == anomaly.document_id
        ).scalar()

    account_code = metadata.get("account_code") or anomaly.field_name
    account_name = metadata.get("account_name")
    if not account_name and account_code:
        account_name = db.query(ChartOfAccounts.account_name).filter(
            ChartOfAccounts.account_code == account_code
        ).scalar()
    actual_value = _safe_float(metadata.get("actual_value")) or _safe_float(anomaly.field_value)
    expected_value = _safe_float(anomaly.expected_value)
    message = metadata.get("message") or (
        f"{account_code} = {anomaly.field_value} (expected: {anomaly.expected_value or 'normal range'})"
    )
    
    return {
        "id": anomaly.id,
        "type": anomaly.anomaly_type,
        "severity": anomaly.severity,
        "message": message,
        "property_id": property_id,
        "account_code": account_code,
        "account_name": account_name,
        "actual_value": actual_value,
        "expected_value": expected_value,
        "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None
    }


@router.get("/{anomaly_id}/detailed")
async def get_anomaly_detailed(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get comprehensive detailed information about a specific anomaly.
    
    Returns:
        Comprehensive anomaly data including:
        - Anomaly details (all fields)
        - XAI explanation (if available)
        - PDF field coordinates (if available)
        - Similar anomalies (same account, different periods)
        - Feedback statistics
        - Cross-property context
        - Learned patterns
        - Model information
    """
    import time
    start_time = time.time()
    
    # Get anomaly - use load_only to avoid loading columns that don't exist in DB
    from sqlalchemy.orm import load_only
    from app.models.document_upload import DocumentUpload
    
    # Load only the columns we actually use to avoid missing column errors
    anomaly = db.query(AnomalyDetection).options(
        load_only(
            AnomalyDetection.id,
            AnomalyDetection.document_id,
            AnomalyDetection.field_name,
            AnomalyDetection.field_value,
            AnomalyDetection.expected_value,
            AnomalyDetection.z_score,
            AnomalyDetection.percentage_change,
            AnomalyDetection.anomaly_type,
            AnomalyDetection.severity,
            AnomalyDetection.confidence,
            AnomalyDetection.detected_at,
            AnomalyDetection.metadata_json
        )
    ).filter(
        AnomalyDetection.id == anomaly_id
    ).first()
    
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found"
        )

    metadata = _parse_metadata(anomaly.metadata_json)
    document = None
    if anomaly.document_id:
        document = db.query(DocumentUpload).filter(DocumentUpload.id == anomaly.document_id).first()

    property_id = metadata.get("property_id")
    if isinstance(property_id, str) and property_id.isdigit():
        property_id = int(property_id)
    if property_id is None and document:
        property_id = document.property_id

    period_id = metadata.get("period_id")
    if isinstance(period_id, str) and period_id.isdigit():
        period_id = int(period_id)
    if period_id is None and document:
        period_id = document.period_id

    document_type = metadata.get("document_type")
    if document_type is None and document:
        document_type = document.document_type

    # Enforce tenancy
    from app.models.property import Property
    if property_id:
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop or prop.organization_id != current_org.id:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anomaly {anomaly_id} not found"
            )
    elif document:
        prop = db.query(Property).filter(Property.id == document.property_id).first()
        if not prop or prop.organization_id != current_org.id:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anomaly {anomaly_id} not found"
            )

    account_code = metadata.get("account_code") or anomaly.field_name
    account_name = metadata.get("account_name")
    if not account_name and account_code:
        account_name = db.query(ChartOfAccounts.account_name).filter(
            ChartOfAccounts.account_code == account_code
        ).scalar()
    actual_value = _safe_float(metadata.get("actual_value")) or _safe_float(anomaly.field_value)
    expected_value = _safe_float(metadata.get("expected_value")) or _safe_float(anomaly.expected_value)

    detection_method = metadata.get("detection_method")
    if isinstance(detection_method, list):
        detection_method = ", ".join([str(item) for item in detection_method if item])

    message = metadata.get("message") or (
        f"{account_code} = {anomaly.field_value} (expected: {anomaly.expected_value or 'normal range'})"
    )

    details = {
        "property_id": property_id,
        "document_id": anomaly.document_id,
        "document_type": document_type,
        "period_id": period_id,
        "period_date": metadata.get("period_date"),
        "metric_name": metadata.get("metric_name"),
        "direction": metadata.get("direction"),
    }

    anomaly_payload = {
        "id": anomaly.id,
        "record_id": anomaly.id,
        "anomaly_type": anomaly.anomaly_type,
        "severity": anomaly.severity,
        "account_code": account_code,
        "account_name": account_name,
        "field_name": anomaly.field_name,
        "actual_value": actual_value,
        "expected_value": expected_value,
        "confidence_score": _safe_float(anomaly.confidence),
        "confidence": _safe_float(anomaly.confidence),
        "z_score": _safe_float(anomaly.z_score),
        "percentage_change": _safe_float(anomaly.percentage_change),
        "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None,
        "message": message,
        "document_id": anomaly.document_id,
        "document_type": document_type,
        "period_id": period_id,
        "context_suppressed": bool(metadata.get("context_suppressed", False)),
        "suppression_reason": metadata.get("suppression_reason"),
        "details": details
    }
    
    result = {
        **anomaly_payload,
        "anomaly": {
            "id": anomaly.id,
            "type": anomaly.anomaly_type,
            "severity": anomaly.severity,
            "message": message,
            "property_id": property_id,
            "account_code": account_code,
            "account_name": account_name,
            "field_name": anomaly.field_name,
            "actual_value": actual_value,
            "expected_value": expected_value,
            "confidence": _safe_float(anomaly.confidence),
            "z_score": _safe_float(anomaly.z_score),
            "percentage_change": _safe_float(anomaly.percentage_change),
            "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None,
            "detection_method": detection_method,
            "context_suppressed": bool(metadata.get("context_suppressed", False)),
            "suppression_reason": metadata.get("suppression_reason")
        },
        "xai_explanation": None,
        "pdf_coordinates": None,
        "similar_anomalies": [],
        "feedback_statistics": None,
        "cross_property_context": None,
        "learned_patterns": [],
        "model_information": None
    }
    
    # Get XAI explanation if available
    try:
        from app.models.anomaly_explanation import AnomalyExplanation
        explanation = db.query(AnomalyExplanation).filter(
            AnomalyExplanation.anomaly_detection_id == anomaly_id
        ).first()
        
        if explanation:
            result["xai_explanation"] = {
                "root_cause_type": explanation.root_cause_type,
                "root_cause_description": explanation.root_cause_description,
                "shap_values": explanation.shap_values,
                "lime_explanation": explanation.lime_explanation,
                "natural_language_explanation": explanation.natural_language_explanation,
                "recommended_actions": explanation.recommended_actions,
                "generated_at": explanation.generated_at.isoformat() if explanation.generated_at else None
            }
    except Exception as e:
        logger.warning(f"Error getting XAI explanation: {e}")
    
    # Get PDF field coordinates if available
    try:
        from app.models.pdf_field_coordinate import PDFFieldCoordinate
        
        if anomaly.document_id:
            coordinates = db.query(PDFFieldCoordinate).filter(
                PDFFieldCoordinate.document_upload_id == anomaly.document_id,
                PDFFieldCoordinate.field_name == anomaly.field_name
            ).first()
            
            if coordinates:
                result["pdf_coordinates"] = {
                    "page_number": coordinates.page_number,
                    "x": float(coordinates.x) if coordinates.x else None,
                    "y": float(coordinates.y) if coordinates.y else None,
                    "width": float(coordinates.x1 - coordinates.x0) if coordinates.x1 is not None and coordinates.x0 is not None else None,
                    "height": float(coordinates.y1 - coordinates.y0) if coordinates.y1 is not None and coordinates.y0 is not None else None,
                    "confidence": float(coordinates.confidence) if coordinates.confidence else None
                }
    except Exception as e:
        logger.warning(f"Error getting PDF coordinates: {e}")
    
    # Get similar anomalies (same account, different periods)
    try:
        from sqlalchemy import and_
        from datetime import datetime, timedelta
        
        similar_query = db.query(AnomalyDetection).options(
            load_only(
                AnomalyDetection.id,
                AnomalyDetection.detected_at,
                AnomalyDetection.field_value,
                AnomalyDetection.expected_value,
                AnomalyDetection.severity
            )
        )

        if property_id is not None:
            similar_query = similar_query.join(
                DocumentUpload,
                DocumentUpload.id == AnomalyDetection.document_id
            ).filter(DocumentUpload.property_id == property_id)

        similar = similar_query.filter(
            and_(
                AnomalyDetection.id != anomaly_id,
                AnomalyDetection.field_name == anomaly.field_name,
                AnomalyDetection.detected_at >= datetime.now() - timedelta(days=365)
            )
        ).order_by(AnomalyDetection.detected_at.desc()).limit(5).all()
        
        result["similar_anomalies"] = [
            {
                "id": s.id,
                "detected_at": s.detected_at.isoformat() if s.detected_at else None,
                "actual_value": _safe_float(s.field_value),
                "expected_value": _safe_float(s.expected_value),
                "severity": s.severity,
                "similarity_score": 0.8  # Would calculate based on value similarity
            }
            for s in similar
        ]
    except Exception as e:
        logger.warning(f"Error getting similar anomalies: {e}")
    
    # Get feedback statistics
    try:
        from app.models.anomaly_feedback import AnomalyFeedback
        from sqlalchemy import func, Integer
        
        feedback_stats = db.query(
            func.count(AnomalyFeedback.id).label('total_feedback'),
            func.sum(func.cast(AnomalyFeedback.feedback_type == 'true_positive', Integer)).label('true_positives'),
            func.sum(func.cast(AnomalyFeedback.feedback_type == 'false_positive', Integer)).label('false_positives')
        ).filter(
            AnomalyFeedback.anomaly_detection_id == anomaly_id
        ).first()
        
        total_feedback = feedback_stats.total_feedback or 0
        true_positives = feedback_stats.true_positives or 0
        false_positives = feedback_stats.false_positives or 0
        
        result["feedback_statistics"] = {
            "total_feedback_count": total_feedback,
            "true_positive_count": true_positives,
            "false_positive_count": false_positives,
            "true_positive_rate": (true_positives / total_feedback * 100) if total_feedback > 0 else None,
            "false_positive_rate": (false_positives / total_feedback * 100) if total_feedback > 0 else None
        }
    except Exception as e:
        logger.warning(f"Error getting feedback statistics: {e}")
    
    # Get cross-property context
    try:
        from app.services.cross_property_intelligence import CrossPropertyIntelligenceService
        cross_property_service = CrossPropertyIntelligenceService(db)
        
        if cross_property_service.enabled and property_id is not None and account_code:
            # Get property ranking
            ranking = cross_property_service.get_property_ranking(
                property_id=property_id,
                account_code=account_code
            )
            
            if ranking:
                result["cross_property_context"] = {
                    "portfolio_rank": ranking.get('rank'),
                    "portfolio_percentile": ranking.get('percentile'),
                    "portfolio_mean": ranking.get('portfolio_mean'),
                    "portfolio_median": ranking.get('portfolio_median'),
                    "portfolio_std": ranking.get('portfolio_std'),
                    "total_properties": ranking.get('total_properties')
                }
    except Exception as e:
        logger.warning(f"Error getting cross-property context: {e}")
    
    # Get learned patterns that apply to this anomaly
    try:
        from app.models.anomaly_feedback import AnomalyLearningPattern
        from sqlalchemy import and_
        
        if property_id is None or not account_code:
            patterns = []
        else:
            patterns = db.query(AnomalyLearningPattern).filter(
                and_(
                    AnomalyLearningPattern.property_id == property_id,
                    AnomalyLearningPattern.account_code == account_code
                )
            ).all()
        
        result["learned_patterns"] = [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "pattern_description": p.pattern_description,
                "confidence": float(p.confidence) if p.confidence else None,
                "suppression_enabled": p.auto_suppress,
                "learned_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patterns
        ]
    except Exception as e:
        logger.warning(f"Error getting learned patterns: {e}")
    
    # Get model information
    result["model_information"] = {
        "detection_method": detection_method,
        "algorithm_used": getattr(anomaly, 'algorithm_used', None),
        "model_version": getattr(anomaly, 'model_version', None),
        "confidence_score": _safe_float(anomaly.confidence)
    }
    
    elapsed_time = time.time() - start_time
    result["response_time_ms"] = elapsed_time * 1000
    
    logger.info(f"Enhanced anomaly detail retrieved in {elapsed_time*1000:.2f}ms for anomaly {anomaly_id}")
    
    return result


@router.get("/{anomaly_id}/contribution-waterfall")
async def get_contribution_waterfall(
    anomaly_id: int,
    top_n: int = Query(5, ge=1, le=20, description="Number of top accounts to include"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get contribution waterfall data for an anomaly using real account values.

    Returns:
        contributions: List of {name, value, type} entries for the chart.
    """
    from app.models.document_upload import DocumentUpload
    from app.models.income_statement_data import IncomeStatementData
    from app.models.balance_sheet_data import BalanceSheetData
    from app.models.cash_flow_data import CashFlowData
    from app.models.rent_roll_data import RentRollData
    from app.models.mortgage_statement_data import MortgageStatementData

    anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found"
        )

    metadata = _parse_metadata(anomaly.metadata_json)
    document = None
    if anomaly.document_id:
        document = db.query(DocumentUpload).filter(DocumentUpload.id == anomaly.document_id).first()

    property_id = metadata.get("property_id")
    if isinstance(property_id, str) and property_id.isdigit():
        property_id = int(property_id)
    if property_id is None and document:
        property_id = document.property_id

    period_id = metadata.get("period_id")
    if isinstance(period_id, str) and period_id.isdigit():
        period_id = int(period_id)
    if period_id is None and document:
        period_id = document.period_id

    document_type = metadata.get("document_type")
    if document_type is None and document:
        document_type = document.document_type

    expected_value = _safe_float(metadata.get("expected_value")) or _safe_float(anomaly.expected_value)
    actual_value = _safe_float(metadata.get("actual_value")) or _safe_float(anomaly.field_value)

    def build_chart(entries, total_override=None):
        cleaned = [e for e in entries if e.get("value") is not None]
        cleaned.sort(key=lambda e: abs(e["value"]), reverse=True)
        top_entries = cleaned[:top_n]
        remainder = cleaned[top_n:]
        if remainder:
            other_value = sum(e["value"] for e in remainder)
            top_entries.append({
                "name": "Other",
                "value": other_value,
                "type": "positive" if other_value >= 0 else "negative"
            })

        contributions = []
        base_value = expected_value if expected_value is not None else 0
        contributions.append({
            "name": "Base Value",
            "value": base_value,
            "type": "total"
        })
        contributions.extend(top_entries)

        if total_override is not None:
            total_value = total_override
        elif actual_value is not None:
            total_value = actual_value
        else:
            total_value = sum(e["value"] for e in cleaned)

        contributions.append({
            "name": "Total",
            "value": total_value,
            "type": "total"
        })

        return contributions

    entries = []

    if document_type == "income_statement":
        query = db.query(IncomeStatementData)
        if anomaly.document_id:
            query = query.filter(IncomeStatementData.upload_id == anomaly.document_id)
        elif property_id and period_id:
            query = query.filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        items = query.filter(
            IncomeStatementData.is_total.is_(False),
            IncomeStatementData.is_subtotal.is_(False)
        ).all()
        for item in items:
            value = _safe_float(item.period_amount)
            if value is None:
                continue
            name = f"{item.account_code} - {item.account_name}"
            entries.append({
                "name": name,
                "value": value,
                "type": "positive" if value >= 0 else "negative"
            })
        return {"contributions": build_chart(entries)}

    if document_type == "balance_sheet":
        query = db.query(BalanceSheetData)
        if anomaly.document_id:
            query = query.filter(BalanceSheetData.upload_id == anomaly.document_id)
        elif property_id and period_id:
            query = query.filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        items = query.filter(
            BalanceSheetData.is_total.is_(False),
            BalanceSheetData.is_subtotal.is_(False)
        ).all()
        for item in items:
            value = _safe_float(item.amount)
            if value is None:
                continue
            name = f"{item.account_code} - {item.account_name}"
            entries.append({
                "name": name,
                "value": value,
                "type": "positive" if value >= 0 else "negative"
            })
        return {"contributions": build_chart(entries)}

    if document_type == "cash_flow":
        query = db.query(CashFlowData)
        if anomaly.document_id:
            query = query.filter(CashFlowData.upload_id == anomaly.document_id)
        elif property_id and period_id:
            query = query.filter(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        items = query.filter(
            CashFlowData.is_total.is_(False),
            CashFlowData.is_subtotal.is_(False)
        ).all()
        for item in items:
            value = _safe_float(item.period_amount)
            if value is None:
                continue
            name = f"{item.account_code} - {item.account_name}"
            entries.append({
                "name": name,
                "value": value,
                "type": "positive" if value >= 0 else "negative"
            })
        return {"contributions": build_chart(entries)}

    if document_type == "rent_roll":
        query = db.query(RentRollData)
        if anomaly.document_id:
            query = query.filter(RentRollData.upload_id == anomaly.document_id)
        elif property_id and period_id:
            query = query.filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        items = query.all()
        for item in items:
            value = _safe_float(item.monthly_rent)
            if value is None:
                value = _safe_float(item.annual_rent)
            if value is None:
                continue
            name = f"{item.unit_number} - {item.tenant_name}"
            entries.append({
                "name": name,
                "value": value,
                "type": "positive" if value >= 0 else "negative"
            })
        return {"contributions": build_chart(entries)}

    if document_type == "mortgage_statement":
        query = db.query(MortgageStatementData)
        if anomaly.document_id:
            query = query.filter(MortgageStatementData.upload_id == anomaly.document_id)
        elif property_id and period_id:
            query = query.filter(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            )
        items = query.all()
        totals = {
            "Principal Due": 0,
            "Interest Due": 0,
            "Tax Escrow Due": 0,
            "Insurance Escrow Due": 0,
            "Reserve Due": 0,
            "Late Fees": 0,
            "Other Fees": 0
        }
        total_payment = 0
        for item in items:
            totals["Principal Due"] += _safe_float(item.principal_due) or 0
            totals["Interest Due"] += _safe_float(item.interest_due) or 0
            totals["Tax Escrow Due"] += _safe_float(item.tax_escrow_due) or 0
            totals["Insurance Escrow Due"] += _safe_float(item.insurance_escrow_due) or 0
            totals["Reserve Due"] += _safe_float(item.reserve_due) or 0
            totals["Late Fees"] += _safe_float(item.late_fees) or 0
            totals["Other Fees"] += _safe_float(item.other_fees) or 0
            total_payment += _safe_float(item.total_payment_due) or 0

        for name, value in totals.items():
            if value == 0:
                continue
            entries.append({
                "name": name,
                "value": float(value),
                "type": "positive" if value >= 0 else "negative"
            })
        total_override = total_payment if total_payment != 0 else None
        return {"contributions": build_chart(entries, total_override=total_override)}

    return {"contributions": build_chart(entries)}


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


@router.get("/export/csv")
async def export_anomalies_csv(
    property_ids: Optional[str] = Query(None, description="Comma-separated property IDs"),
    date_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    severity: Optional[str] = Query(None, description="Severity filter (critical, high, medium, low)"),
    anomaly_type: Optional[str] = Query(None, description="Anomaly type filter"),
    account_codes: Optional[str] = Query(None, description="Comma-separated account codes"),
    include_explanations: bool = Query(True, description="Include XAI explanations"),
    include_feedback: bool = Query(True, description="Include feedback history"),
    include_cross_property: bool = Query(True, description="Include cross-property context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export anomalies to CSV format."""
    try:
        property_id_list = [int(p.strip()) for p in property_ids.split(',')] if property_ids else None
        account_code_list = [c.strip() for c in account_codes.split(',')] if account_codes else None
        export_service = AnomalyExportService(db)
        csv_bytes = export_service.export_anomalies(
            format='csv', property_ids=property_id_list, date_start=date_start, date_end=date_end,
            severity=severity, anomaly_type=anomaly_type, account_codes=account_code_list,
            include_explanations=include_explanations, include_feedback=include_feedback,
            include_cross_property=include_cross_property
        )
        filename = f"anomalies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(content=csv_bytes, media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "text/csv; charset=utf-8"})
    except Exception as e:
        logger.error(f"Error exporting anomalies to CSV: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export anomalies: {str(e)}")


@router.get("/export/excel")
async def export_anomalies_excel(
    property_ids: Optional[str] = Query(None, description="Comma-separated property IDs"),
    date_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    severity: Optional[str] = Query(None, description="Severity filter (critical, high, medium, low)"),
    anomaly_type: Optional[str] = Query(None, description="Anomaly type filter"),
    account_codes: Optional[str] = Query(None, description="Comma-separated account codes"),
    include_explanations: bool = Query(True, description="Include XAI explanations"),
    include_feedback: bool = Query(True, description="Include feedback history"),
    include_cross_property: bool = Query(True, description="Include cross-property context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export anomalies to Excel format (XLSX)."""
    try:
        property_id_list = [int(p.strip()) for p in property_ids.split(',')] if property_ids else None
        account_code_list = [c.strip() for c in account_codes.split(',')] if account_codes else None
        export_service = AnomalyExportService(db)
        excel_bytes = export_service.export_anomalies(
            format='xlsx', property_ids=property_id_list, date_start=date_start, date_end=date_end,
            severity=severity, anomaly_type=anomaly_type, account_codes=account_code_list,
            include_explanations=include_explanations, include_feedback=include_feedback,
            include_cross_property=include_cross_property
        )
        filename = f"anomalies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting anomalies to Excel: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export anomalies: {str(e)}")


@router.get("/export/json")
async def export_anomalies_json(
    property_ids: Optional[str] = Query(None, description="Comma-separated property IDs"),
    date_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    severity: Optional[str] = Query(None, description="Severity filter (critical, high, medium, low)"),
    anomaly_type: Optional[str] = Query(None, description="Anomaly type filter"),
    account_codes: Optional[str] = Query(None, description="Comma-separated account codes"),
    include_explanations: bool = Query(True, description="Include XAI explanations"),
    include_feedback: bool = Query(True, description="Include feedback history"),
    include_cross_property: bool = Query(True, description="Include cross-property context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export anomalies to JSON format."""
    try:
        property_id_list = [int(p.strip()) for p in property_ids.split(',')] if property_ids else None
        account_code_list = [c.strip() for c in account_codes.split(',')] if account_codes else None
        export_service = AnomalyExportService(db)
        json_bytes = export_service.export_anomalies(
            format='json', property_ids=property_id_list, date_start=date_start, date_end=date_end,
            severity=severity, anomaly_type=anomaly_type, account_codes=account_code_list,
            include_explanations=include_explanations, include_feedback=include_feedback,
            include_cross_property=include_cross_property
        )
        filename = f"anomalies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return Response(content=json_bytes, media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        logger.error(f"Error exporting anomalies to JSON: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export anomalies: {str(e)}")


@router.get("/uncertain")
async def get_uncertain_anomalies(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of anomalies to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get anomalies most needing user feedback (uncertain anomalies)."""
    try:
        from sqlalchemy import and_, or_, func
        from datetime import timedelta
        query = db.query(AnomalyDetection, func.count(AnomalyFeedback.id).label('feedback_count')
        ).outerjoin(AnomalyFeedback, AnomalyFeedback.anomaly_detection_id == AnomalyDetection.id
        ).filter(and_(or_(AnomalyDetection.confidence.is_(None), AnomalyDetection.confidence < 0.9),
            AnomalyDetection.context_suppressed == False)).group_by(AnomalyDetection.id).having(
            func.count(AnomalyFeedback.id) < 3)
        results = query.all()
        uncertain_anomalies = []
        current_date = datetime.now()
        for anomaly, feedback_count in results:
            days_since = (current_date - anomaly.detected_at).days if anomaly.detected_at else 0
            confidence = float(anomaly.confidence) if anomaly.confidence else 0.5
            uncertainty_score = ((1 - confidence) * (1 + days_since / 30) * (1 - min(feedback_count, 10) / 10))
            similar_count = db.query(AnomalyDetection).filter(and_(
                AnomalyDetection.id != anomaly.id, AnomalyDetection.account_code == anomaly.account_code,
                AnomalyDetection.property_id == anomaly.property_id,
                AnomalyDetection.detected_at >= current_date - timedelta(days=365))).count()
            uncertain_anomalies.append({'anomaly': anomaly, 'uncertainty_score': uncertainty_score,
                'confidence': confidence, 'days_since_detection': days_since, 'feedback_count': feedback_count,
                'similar_anomalies_count': similar_count})
        uncertain_anomalies.sort(key=lambda x: x['uncertainty_score'], reverse=True)
        uncertain_anomalies = uncertain_anomalies[:limit]
        return [{"id": item['anomaly'].id, "property_id": item['anomaly'].property_id,
            "account_code": item['anomaly'].account_code, "field_name": item['anomaly'].field_name,
            "anomaly_type": item['anomaly'].anomaly_type, "severity": item['anomaly'].severity,
            "actual_value": float(item['anomaly'].actual_value) if item['anomaly'].actual_value else None,
            "expected_value": float(item['anomaly'].expected_value) if item['anomaly'].expected_value else None,
            "confidence": item['confidence'], "uncertainty_score": item['uncertainty_score'],
            "days_since_detection": item['days_since_detection'], "feedback_count": item['feedback_count'],
            "similar_anomalies_count": item['similar_anomalies_count'],
            "detected_at": item['anomaly'].detected_at.isoformat() if item['anomaly'].detected_at else None,
            "message": item['anomaly'].message or f"Anomaly detected in {item['anomaly'].account_code}"}
            for item in uncertain_anomalies]
    except Exception as e:
        logger.error(f"Error getting uncertain anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get uncertain anomalies: {str(e)}")
