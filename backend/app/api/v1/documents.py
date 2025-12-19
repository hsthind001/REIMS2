"""
Document Upload API - Complete workflow for financial document management
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends, Form
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from typing import Optional, List
from decimal import Decimal

from app.db.database import get_db
from app.db.minio_client import get_file_url, delete_file
from app.services.document_service import DocumentService
from app.services.pdf_generator_service import PDFGeneratorService
from app.tasks.extraction_tasks import extract_document
from fastapi.responses import StreamingResponse
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.financial_metrics import FinancialMetrics
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.models.extraction_log import ExtractionLog
from app.schemas.document import (
    DocumentTypeEnum,
    ExtractionStatusEnum,
    DocumentUploadResponse,
    DocumentUploadDetail,
    DocumentListResponse,
    DocumentListItem,
    ExtractedDataResponse,
    BalanceSheetDataItem,
    IncomeStatementDataItem,
    CashFlowDataItem,
    RentRollDataItem,
    FinancialMetricsData,
    ValidationResultItem,
    DocumentDownloadResponse
)

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    property_code: str = Form(..., description="Property code (e.g., WEND001)"),
    period_year: int = Form(..., ge=2000, le=2100, description="Financial period year"),
    period_month: int = Form(..., ge=1, le=12, description="Financial period month (1-12)"),
    document_type: DocumentTypeEnum = Form(..., description="Type of financial document"),
    file: UploadFile = File(..., description="PDF file to upload"),
    force_overwrite: bool = Form(False, description="Force overwrite if file exists"),
    db: Session = Depends(get_db)
):
    """
    Upload financial document and trigger extraction
    
    **Workflow:**
    1. Validate property exists
    2. Create/get financial period
    3. Check for duplicate (by file hash)
    4. If duplicate found: AUTO-DELETE old upload and replace with new one
    5. Upload file to MinIO
    6. Create document_uploads record
    7. Trigger Celery task for extraction
    8. Return upload_id and task_id
    
    **Duplicate Handling (Auto-Replace):**
    - Uses MD5 hash of file content to detect duplicates
    - If duplicate found: Automatically deletes old upload (including all related financial data)
    - Old file removed from MinIO
    - New file uploaded and extracted
    - Prevents failed uploads from blocking new attempts
    
    **Returns:**
    - upload_id: Unique identifier for tracking
    - task_id: Celery task ID for extraction status
    - file_path: Storage path in MinIO
    """
    # Validate file type
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF (application/pdf)"
        )
    
    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )
    
    try:
        # Create document service
        doc_service = DocumentService(db)
        
        # Upload document
        result = await doc_service.upload_document(
            property_code=property_code,
            period_year=period_year,
            period_month=period_month,
            document_type=document_type.value,
            file=file,
            uploaded_by=None,  # TODO: Get from auth context
            force_overwrite=force_overwrite
        )
        
        # Check for property mismatch
        if result.get("property_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "property_mismatch",
                    "message": result["message"],
                    "selected_property_code": result["selected_property_code"],
                    "selected_property_name": result["selected_property_name"],
                    "detected_property_code": result["detected_property_code"],
                    "detected_property_name": result["detected_property_name"],
                    "confidence": result["confidence"],
                    "matches_found": result.get("matches_found", [])
                }
            )
        
        # Check for document type mismatch
        if result.get("type_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "document_type_mismatch",
                    "message": result["message"],
                    "selected_type": result["selected_type"],
                    "detected_type": result["detected_type"],
                    "confidence": result["confidence"],
                    "keywords_found": result.get("keywords_found", [])
                }
            )
        
        # Check for year mismatch
        if result.get("year_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "year_mismatch",
                    "message": result["message"],
                    "selected_year": result["selected_year"],
                    "detected_year": result["detected_year"],
                    "period_text": result.get("period_text", ""),
                    "confidence": result["confidence"]
                }
            )
        
        # Check for month/period mismatch
        if result.get("period_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "period_mismatch",
                    "message": result["message"],
                    "selected_month": result["selected_month"],
                    "detected_month": result["detected_month"],
                    "selected_month_name": result["selected_month_name"],
                    "detected_month_name": result["detected_month_name"],
                    "period_text": result.get("period_text", ""),
                    "confidence": result["confidence"]
                }
            )
        
        # Check if file already exists (and not forcing overwrite)
        if result.get("file_exists"):
            return DocumentUploadResponse(
                upload_id=None,
                task_id=None,
                message=result["message"],
                file_path=None,
                extraction_status=None,
                file_exists=True,
                existing_file=result.get("existing_file")
            )
        
        # Check if duplicate (by hash)
        if result.get("is_duplicate"):
            return DocumentUploadResponse(
                upload_id=result["upload_id"],
                task_id="N/A",
                message="Duplicate file already exists - no extraction triggered",
                file_path=result["file_path"],
                extraction_status="completed"
            )
        
        # Trigger Celery extraction task with error handling
        try:
            task = extract_document.delay(result["upload_id"])
            task_id = task.id
            extraction_status = "pending"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to queue extraction for upload_id={result['upload_id']}: {e}")
            # Don't fail the upload - file is in MinIO, extraction will be recovered
            task_id = None
            extraction_status = "pending"  # Background task will pick it up
        
        return DocumentUploadResponse(
            upload_id=result["upload_id"],
            task_id=task_id,
            message=result["message"],
            file_path=result["file_path"],
            extraction_status=extraction_status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/documents/bulk-upload", status_code=status.HTTP_201_CREATED)
async def bulk_upload_documents(
    property_code: str = Form(..., description="Property code (e.g., WEND001)"),
    year: int = Form(..., ge=2000, le=2100, description="Year for all documents"),
    files: List[UploadFile] = File(..., description="Multiple files to upload (PDF, CSV, Excel, DOC)"),
    duplicate_strategy: str = Form("skip", description="How to handle duplicates: 'skip' (default), 'replace', or 'version'"),
    uploaded_by: Optional[int] = Form(None, description="User ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Bulk upload multiple documents for a year with intelligent duplicate handling.

    **Features:**
    - Auto-detects document type from filename
    - Auto-detects month from filename (defaults to January if not found)
    - Supports PDF, CSV, Excel (.xlsx, .xls), DOC (.doc, .docx)
    - Intelligently organizes files in MinIO buckets
    - Queues extraction tasks automatically
    - Smart duplicate handling with user control

    **Duplicate Handling Strategies:**
    - **skip** (default): Skip files where documents already exist for that property/period/type
    - **replace**: Replace existing documents with new uploads (deletes old data)
    - **version**: Create new version and keep both (future feature)

    **Filename Patterns:**
    - Document type: *balance*sheet*, *income*statement*, *cash*flow*, *rent*roll*
    - Month: Numeric (1-12), month name (January-December), quarter (Q1-Q4)

    **Returns:**
    - Results per file with status (success/skipped/replaced/failed)
    - Summary counts and duplicate statistics
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files allowed per bulk upload"
        )
    
    try:
        # Create document service
        doc_service = DocumentService(db)

        # Bulk upload documents with duplicate strategy
        result = await doc_service.bulk_upload_documents(
            property_code=property_code,
            year=year,
            files=files,
            uploaded_by=uploaded_by,
            duplicate_strategy=duplicate_strategy
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upload failed: {str(e)}"
        )


@router.get("/documents/queue-status")
async def get_queue_status(db: Session = Depends(get_db)):
    """Get Celery queue status and pending extractions"""
    from celery import current_app
    from app.models.document_upload import DocumentUpload
    
    try:
        # Get Celery inspect object
        inspect = current_app.control.inspect()
        
        # Get active, scheduled, and reserved tasks
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        
        # Count extraction tasks across all workers
        extraction_tasks = 0
        for worker_tasks in [active, scheduled, reserved].values():
            if worker_tasks:
                for tasks in worker_tasks.values():
                    extraction_tasks += len([
                        t for t in tasks 
                        if 'extract_document' in t.get('name', '') or 
                           'extract_document' in str(t.get('task', ''))
                    ])
        
        # Get worker stats
        stats = inspect.stats() or {}
        workers_available = len(stats)
        
        # Count pending uploads
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        
        return {
            "queue_depth": extraction_tasks,
            "workers_available": workers_available,
            "pending_uploads": pending_uploads,
            "workers": list(stats.keys()) if stats else []
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get queue status: {e}")
        # Return safe defaults if Celery is unavailable
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        return {
            "queue_depth": 0,
            "workers_available": 0,
            "pending_uploads": pending_uploads,
            "workers": [],
            "error": "Celery unavailable"
        }


@router.get("/documents/uploads", response_model=DocumentListResponse)
async def list_uploads(
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    document_type: Optional[DocumentTypeEnum] = Query(None, description="Filter by document type"),
    extraction_status: Optional[ExtractionStatusEnum] = Query(None, description="Filter by extraction status"),
    period_year: Optional[int] = Query(None, description="Filter by period year"),
    period_month: Optional[int] = Query(None, description="Filter by period month"),
    is_active: Optional[bool] = Query(True, description="Filter by active status (default: True, only current versions)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    List all uploaded documents with filters
    
    **Filters:**
    - property_code: Filter by specific property
    - document_type: Filter by document type
    - extraction_status: Filter by extraction status
    - period_year/period_month: Filter by financial period
    - is_active: Filter by active status (default: True, shows only current versions)
    
    **Pagination:**
    - skip: Number of records to skip
    - limit: Maximum records to return (max 500)
    
    **Returns:**
    - Paginated list of document uploads with metadata (only active versions by default)
    """
    try:
        # Build query with joins
        query = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        )
        
        # Apply filters
        if property_code:
            query = query.filter(Property.property_code == property_code)
        
        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type.value)
        
        if extraction_status:
            query = query.filter(DocumentUpload.extraction_status == extraction_status.value)
        
        if period_year:
            query = query.filter(FinancialPeriod.period_year == period_year)
        
        if period_month:
            query = query.filter(FinancialPeriod.period_month == period_month)
        
        # Filter by active status (default: only show current versions)
        if is_active is not None:
            query = query.filter(DocumentUpload.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        results = query.order_by(DocumentUpload.upload_date.desc()).offset(skip).limit(limit).all()
        
        # Build response items
        items = []
        for upload, prop_code, year, month, confidence in results:
            items.append(DocumentListItem(
                id=upload.id,
                property_code=prop_code,
                period_year=year,
                period_month=month,
                document_type=upload.document_type,
                file_name=upload.file_name,
                upload_date=upload.upload_date,
                extraction_status=upload.extraction_status,
                extraction_confidence=float(confidence) if confidence else None,
                version=upload.version,
                is_active=upload.is_active
            ))
        
        return DocumentListResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=items
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list uploads: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}", response_model=DocumentUploadDetail)
async def get_upload_status(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Get extraction status and details for an upload
    
    **Returns:**
    - Complete upload record with extraction status
    - Extraction quality metrics (if available)
    - Property and period information
    """
    try:
        # Query with joins
        result = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score,
            ExtractionLog.quality_level,
            ExtractionLog.needs_review
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        ).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        upload, prop_code, year, month, confidence, quality, needs_review = result
        
        return DocumentUploadDetail(
            id=upload.id,
            property_id=upload.property_id,
            period_id=upload.period_id,
            property_code=prop_code,
            period_year=year,
            period_month=month,
            document_type=upload.document_type,
            file_name=upload.file_name,
            file_path=upload.file_path,
            file_hash=upload.file_hash,
            file_size_bytes=upload.file_size_bytes,
            upload_date=upload.upload_date,
            uploaded_by=upload.uploaded_by,
            extraction_status=upload.extraction_status,
            extraction_started_at=upload.extraction_started_at,
            extraction_completed_at=upload.extraction_completed_at,
            extraction_id=upload.extraction_id,
            extraction_confidence=float(confidence) if confidence else None,
            extraction_quality=quality,
            needs_review=needs_review,
            version=upload.version,
            is_active=upload.is_active,
            notes=upload.notes
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload status: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}/data", response_model=ExtractedDataResponse)
async def get_extracted_data(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Get extracted financial data from upload
    
    **Returns:**
    - Balance sheet data (if applicable)
    - Income statement data (if applicable)
    - Cash flow data (if applicable)
    - Rent roll data (if applicable)
    - Financial metrics (if calculated)
    - Validation results (if available)
    """
    try:
        # Get upload with property and period info
        upload_query = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        ).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        upload, prop_code, year, month, confidence = upload_query
        
        # Initialize response
        response = ExtractedDataResponse(
            upload_id=upload.id,
            property_code=prop_code,
            period_year=year,
            period_month=month,
            document_type=upload.document_type,
            extraction_status=upload.extraction_status,
            extraction_confidence=float(confidence) if confidence else None,
            balance_sheet_data=[],
            income_statement_data=[],
            cash_flow_data=[],
            rent_roll_data=[],
            financial_metrics=None,
            validation_results=[],
            validation_passed=True,
            validation_summary={}
        )
        
        # Get financial data based on document type
        if upload.document_type == "balance_sheet":
            bs_items = db.query(BalanceSheetData).filter(
                BalanceSheetData.upload_id == upload_id
            ).all()
            
            response.balance_sheet_data = [
                BalanceSheetDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    amount=float(item.amount),
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in bs_items
            ]
        
        elif upload.document_type == "income_statement":
            is_items = db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload_id
            ).all()
            
            response.income_statement_data = [
                IncomeStatementDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    period_amount=float(item.period_amount),
                    ytd_amount=float(item.ytd_amount) if item.ytd_amount else None,
                    period_percentage=float(item.period_percentage) if item.period_percentage else None,
                    ytd_percentage=float(item.ytd_percentage) if item.ytd_percentage else None,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in is_items
            ]
        
        elif upload.document_type == "cash_flow":
            cf_items = db.query(CashFlowData).filter(
                CashFlowData.upload_id == upload_id
            ).all()
            
            response.cash_flow_data = [
                CashFlowDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    period_amount=float(item.period_amount),
                    cash_flow_category=item.cash_flow_category,
                    is_inflow=item.is_inflow,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in cf_items
            ]
        
        elif upload.document_type == "rent_roll":
            rr_items = db.query(RentRollData).filter(
                RentRollData.upload_id == upload_id
            ).all()
            
            response.rent_roll_data = [
                RentRollDataItem(
                    unit_number=item.unit_number,
                    tenant_name=item.tenant_name,
                    lease_start_date=item.lease_start_date,
                    lease_end_date=item.lease_end_date,
                    unit_area_sqft=float(item.unit_area_sqft) if item.unit_area_sqft else None,
                    monthly_rent=float(item.monthly_rent) if item.monthly_rent else None,
                    annual_rent=float(item.annual_rent) if item.annual_rent else None,
                    occupancy_status=item.occupancy_status,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in rr_items
            ]
        
        # Get financial metrics (if available)
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == upload.property_id,
            FinancialMetrics.period_id == upload.period_id
        ).first()
        
        if metrics:
            response.financial_metrics = FinancialMetricsData(
                total_assets=float(metrics.total_assets) if metrics.total_assets else None,
                total_liabilities=float(metrics.total_liabilities) if metrics.total_liabilities else None,
                total_equity=float(metrics.total_equity) if metrics.total_equity else None,
                total_revenue=float(metrics.total_revenue) if metrics.total_revenue else None,
                total_expenses=float(metrics.total_expenses) if metrics.total_expenses else None,
                net_operating_income=float(metrics.net_operating_income) if metrics.net_operating_income else None,
                net_income=float(metrics.net_income) if metrics.net_income else None,
                occupancy_rate=float(metrics.occupancy_rate) if metrics.occupancy_rate else None,
                debt_service_coverage_ratio=float(metrics.debt_service_coverage_ratio) if metrics.debt_service_coverage_ratio else None
            )
        
        # Get validation results
        validation_results = db.query(
            ValidationResult,
            ValidationRule.rule_name
        ).join(
            ValidationRule, ValidationResult.rule_id == ValidationRule.id
        ).filter(
            ValidationResult.upload_id == upload_id
        ).all()
        
        if validation_results:
            response.validation_results = [
                ValidationResultItem(
                    rule_id=vr.rule_id,
                    rule_name=rule_name,
                    passed=vr.passed,
                    expected_value=float(vr.expected_value) if vr.expected_value else None,
                    actual_value=float(vr.actual_value) if vr.actual_value else None,
                    difference=float(vr.difference) if vr.difference else None,
                    difference_percentage=float(vr.difference_percentage) if vr.difference_percentage else None,
                    error_message=vr.error_message,
                    severity=vr.severity
                )
                for vr, rule_name in validation_results
            ]
            
            # Calculate validation summary
            total_checks = len(validation_results)
            passed_checks = sum(1 for vr, _ in validation_results if vr.passed)
            failed_checks = total_checks - passed_checks
            
            response.validation_passed = failed_checks == 0
            response.validation_summary = {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks
            }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get extracted data: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}/download", response_model=DocumentDownloadResponse)
async def get_download_url(
    upload_id: int,
    expires_in_seconds: int = Query(3600, ge=60, le=86400, description="URL expiry time in seconds (1 hour default, max 24 hours)"),
    db: Session = Depends(get_db)
):
    """
    Get presigned download URL for uploaded document
    
    **Returns:**
    - Presigned URL valid for specified duration (default 1 hour)
    - File metadata
    
    **Note:** URL expires after specified time for security
    """
    try:
        # Get upload record
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Generate presigned URL
        download_url = get_file_url(
            object_name=upload.file_path,
            expires_seconds=expires_in_seconds
        )
        
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        return DocumentDownloadResponse(
            upload_id=upload.id,
            file_name=upload.file_name,
            file_size_bytes=upload.file_size_bytes,
            download_url=download_url,
            expires_in_seconds=expires_in_seconds
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get download URL: {str(e)}"
        )


@router.post("/documents/uploads/reprocess-failed", status_code=status.HTTP_200_OK)
async def reprocess_failed_uploads(
    db: Session = Depends(get_db)
):
    """
    Reprocess all failed document uploads
    
    **Operation:**
    - Finds all documents with extraction_status = 'failed' or containing 'failed'
    - Resets their status to 'pending'
    - Queues them for extraction again
    - Returns count of queued documents
    
    **Returns:**
    - Count of failed documents queued for reprocessing
    """
    try:
        # Find all failed uploads
        from sqlalchemy import or_
        failed_uploads = db.query(DocumentUpload).filter(
            or_(
                DocumentUpload.extraction_status == 'failed',
                DocumentUpload.extraction_status.like('%failed%')
            )
        ).all()
        
        queued_count = 0
        
        for upload in failed_uploads:
            try:
                # Reset status to pending
                upload.extraction_status = 'pending'
                upload.extraction_task_id = None
                upload.extraction_started_at = None
                upload.extraction_completed_at = None
                db.flush()
                
                # Queue extraction task
                task = extract_document.delay(upload.id)
                upload.extraction_task_id = task.id
                db.commit()
                
                queued_count += 1
            except Exception as e:
                db.rollback()
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to reprocess upload_id={upload.id}: {str(e)}")
        
        return {
            "message": f"Successfully queued {queued_count} failed document(s) for reprocessing",
            "queued_count": queued_count,
            "total_failed": len(failed_uploads)
        }
    
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to reprocess failed uploads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess failed uploads: {str(e)}"
        )


@router.delete("/documents/uploads/delete-all-history", status_code=status.HTTP_200_OK)
async def delete_all_upload_history(
    db: Session = Depends(get_db)
):
    """
    Delete all document upload history from the database
    
    **Warning:** This operation:
    - Deletes ALL document upload records from the database
    - Deletes associated extracted financial data (via cascade)
    - Deletes files from MinIO storage
    - This action CANNOT be undone
    
    **Use Cases:**
    - Clean up old upload history
    - Reset system for testing
    - Remove all document records
    
    **Returns:**
    - Count of deleted records
    """
    try:
        # Get all document uploads
        all_uploads = db.query(DocumentUpload).all()
        deleted_count = len(all_uploads)
        
        # Delete files from MinIO and database records
        for upload in all_uploads:
            # Delete file from MinIO if file_path exists
            if upload.file_path:
                try:
                    delete_file(upload.file_path)
                except Exception as e:
                    # Log error but continue deletion
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to delete file from MinIO: {upload.file_path}, error: {str(e)}")
            
            # Delete database record (cascade will handle related data)
            db.delete(upload)
        
        # Commit all deletions
        db.commit()
        
        return {
            "message": f"Successfully deleted {deleted_count} document upload records",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to delete upload history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete upload history: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}/regenerate-pdf")
async def regenerate_income_statement_pdf(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Regenerate income statement PDF from database data
    
    Creates a new PDF matching the original format using extracted data from the database.
    This allows you to verify that extracted values match the original PDF.
    
    **Supported Document Types:**
    - income_statement
    
    **Returns:**
    - PDF file matching original format
    
    **Example Usage:**
    1. Upload ESP 2023 Income Statement
    2. Extract data (already done)
    3. Call this endpoint to regenerate PDF
    4. Compare original vs regenerated PDF to verify extraction accuracy
    """
    try:
        # Get upload record
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        if upload.document_type != "income_statement":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This endpoint only supports income statements. Document type: {upload.document_type}"
            )
        
        # Generate PDF
        generator = PDFGeneratorService()
        pdf_bytes = generator.generate_income_statement_pdf(upload_id, db)
        
        # Generate filename
        filename = upload.file_name or f"income_statement_{upload_id}.pdf"
        # Add "regenerated_" prefix
        if not filename.startswith("regenerated_"):
            filename = f"regenerated_{filename}"
        
        # Return PDF as streaming response
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate PDF: {str(e)}"
        )

